// -*- mode: c++; c-basic-offset: 2; indent-tabs-mode: nil; -*-
// Clock with weather display - combines clock functionality with
// current weather from OpenWeather API displayed on a second line.
//
// This code is public domain
// (but note, that the led-matrix library this depends on is GPL v2)

#include "led-matrix.h"
#include "graphics.h"

#include <getopt.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <iostream>
#include <sstream>
#include <fstream>
#include <curl/curl.h>

#include <vector>
#include <string>
#include <map>

#ifndef TIMER_ABSTIME
#define TIMER_ABSTIME 1
#endif

#ifdef __APPLE__
#include <sys/time.h>
static int clock_nanosleep(clockid_t clock_id, int flags,
                           const struct timespec *request,
                           struct timespec *remain) {
  (void)clock_id;
  if (flags == TIMER_ABSTIME) {
    struct timeval now_tv;
    gettimeofday(&now_tv, NULL);
    struct timespec now;
    now.tv_sec = now_tv.tv_sec;
    now.tv_nsec = now_tv.tv_usec * 1000;
    struct timespec diff;
    diff.tv_sec = request->tv_sec - now.tv_sec;
    diff.tv_nsec = request->tv_nsec - now.tv_nsec;
    if (diff.tv_nsec < 0) {
      diff.tv_sec--;
      diff.tv_nsec += 1000000000;
    }
    if (diff.tv_sec < 0) return 0;
    return nanosleep(&diff, remain);
  }
  return nanosleep(request, remain);
}
#endif

using namespace rgb_matrix;

volatile bool interrupt_received = false;
static void InterruptHandler(int signo) {
  interrupt_received = true;
}

// Weather data structure
struct WeatherData {
  float temp;
  float feels_like;
  float humidity;
  float wind_speed;
  std::string condition_main;
  std::string condition_description;
  time_t timestamp;
  bool valid;
  
  WeatherData() : temp(0), feels_like(0), humidity(0), wind_speed(0),
                  condition_main("Unknown"), condition_description(""),
                  timestamp(0), valid(false) {}
};

// Callback for curl to write response data
static size_t WriteCallback(void *contents, size_t size, size_t nmemb, void *userp) {
  ((std::string*)userp)->append((char*)contents, size * nmemb);
  return size * nmemb;
}

// Simple JSON value extractor (basic implementation)
// Supports nested keys like "main.temp" or "wind.speed"
static std::string extractJsonValue(const std::string &json, const std::string &key) {
  size_t pos = 0;
  std::string remaining_json = json;
  
  // Handle nested keys (e.g., "main.temp")
  size_t dot_pos = key.find('.');
  if (dot_pos != std::string::npos) {
    std::string parent_key = key.substr(0, dot_pos);
    std::string child_key = key.substr(dot_pos + 1);
    
    // Find parent object
    std::string parent_search = "\"" + parent_key + "\"";
    pos = remaining_json.find(parent_search);
    if (pos == std::string::npos) return "";
    
    // Find opening brace after parent key
    pos = remaining_json.find("{", pos);
    if (pos == std::string::npos) return "";
    
    // Find matching closing brace
    int brace_count = 0;
    size_t end_pos = pos;
    for (size_t i = pos; i < remaining_json.length(); i++) {
      if (remaining_json[i] == '{') brace_count++;
      if (remaining_json[i] == '}') {
        brace_count--;
        if (brace_count == 0) {
          end_pos = i + 1;
          break;
        }
      }
    }
    remaining_json = remaining_json.substr(pos, end_pos - pos);
    return extractJsonValue(remaining_json, child_key);
  }
  
  // Simple key extraction
  std::string search_key = "\"" + key + "\"";
  pos = remaining_json.find(search_key);
  if (pos == std::string::npos) return "";
  
  pos = remaining_json.find(":", pos);
  if (pos == std::string::npos) return "";
  pos++;
  
  // Skip whitespace
  while (pos < remaining_json.length() && (remaining_json[pos] == ' ' || remaining_json[pos] == '\t')) pos++;
  
  if (pos >= remaining_json.length()) return "";
  
  std::string value;
  if (remaining_json[pos] == '"') {
    // String value
    pos++;
    while (pos < remaining_json.length() && remaining_json[pos] != '"') {
      if (remaining_json[pos] == '\\' && pos + 1 < remaining_json.length()) {
        pos++;
        if (remaining_json[pos] == 'n') value += '\n';
        else if (remaining_json[pos] == 't') value += '\t';
        else value += remaining_json[pos];
      } else {
        value += remaining_json[pos];
      }
      pos++;
    }
  } else {
    // Numeric or boolean value
    while (pos < remaining_json.length() && remaining_json[pos] != ',' && remaining_json[pos] != '}' && 
           remaining_json[pos] != ']' && remaining_json[pos] != ' ' && remaining_json[pos] != '\n') {
      value += remaining_json[pos];
      pos++;
    }
  }
  return value;
}

// Fetch weather from OpenWeather API
static WeatherData fetchWeather(const std::string &api_key, double lat, double lon, 
                                 const std::string &units, const std::string &lang) {
  WeatherData weather;
  
  CURL *curl = curl_easy_init();
  if (!curl) {
    fprintf(stderr, "Failed to initialize curl\n");
    return weather;
  }
  
  std::string url = "https://api.openweathermap.org/data/2.5/weather";
  std::stringstream url_params;
  url_params << url << "?lat=" << lat << "&lon=" << lon 
             << "&appid=" << api_key << "&units=" << units << "&lang=" << lang;
  
  std::string response_data;
  
  curl_easy_setopt(curl, CURLOPT_URL, url_params.str().c_str());
  curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
  curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_data);
  curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);
  
  CURLcode res = curl_easy_perform(curl);
  
  if (res != CURLE_OK) {
    fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
    curl_easy_cleanup(curl);
    return weather;
  }
  
  long response_code;
  curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
  curl_easy_cleanup(curl);
  
  if (response_code != 200) {
    fprintf(stderr, "API returned status code: %ld\n", response_code);
    return weather;
  }
  
  // Parse JSON response - use nested key notation
  std::string temp_str = extractJsonValue(response_data, "main.temp");
  std::string feels_str = extractJsonValue(response_data, "main.feels_like");
  std::string humidity_str = extractJsonValue(response_data, "main.humidity");
  
  // Extract weather array (first element) - find weather array and extract first object
  size_t weather_start = response_data.find("\"weather\"");
  if (weather_start != std::string::npos) {
    size_t array_start = response_data.find("[", weather_start);
    if (array_start != std::string::npos) {
      size_t obj_start = response_data.find("{", array_start);
      if (obj_start != std::string::npos) {
        // Find matching closing brace for first weather object
        int brace_count = 0;
        size_t obj_end = obj_start;
        for (size_t i = obj_start; i < response_data.length(); i++) {
          if (response_data[i] == '{') brace_count++;
          if (response_data[i] == '}') {
            brace_count--;
            if (brace_count == 0) {
              obj_end = i + 1;
              break;
            }
          }
        }
        std::string weather_obj = response_data.substr(obj_start, obj_end - obj_start);
        weather.condition_main = extractJsonValue(weather_obj, "main");
        weather.condition_description = extractJsonValue(weather_obj, "description");
      }
    }
  }
  
  // Extract wind speed
  std::string wind_str = extractJsonValue(response_data, "wind.speed");
  
  // Extract timestamp
  std::string dt_str = extractJsonValue(response_data, "dt");
  
  // Parse numeric values
  if (!temp_str.empty()) weather.temp = atof(temp_str.c_str());
  if (!feels_str.empty()) weather.feels_like = atof(feels_str.c_str());
  if (!humidity_str.empty()) weather.humidity = atof(humidity_str.c_str());
  if (!wind_str.empty()) weather.wind_speed = atof(wind_str.c_str());
  if (!dt_str.empty()) weather.timestamp = (time_t)atol(dt_str.c_str());
  
  weather.valid = true;
  return weather;
}

// Load environment variables from .env file or system env
static void loadEnv(std::map<std::string, std::string> &env_map) {
  // Try to read .env file first
  std::ifstream env_file(".env");
  if (env_file.is_open()) {
    std::string line;
    while (std::getline(env_file, line)) {
      size_t eq_pos = line.find('=');
      if (eq_pos != std::string::npos && line[0] != '#') {
        std::string key = line.substr(0, eq_pos);
        std::string value = line.substr(eq_pos + 1);
        // Remove quotes if present
        if (value.length() >= 2 && value[0] == '"' && value[value.length()-1] == '"') {
          value = value.substr(1, value.length() - 2);
        }
        env_map[key] = value;
      }
    }
    env_file.close();
  }
  
  // Override with system environment variables
  const char *api_key = getenv("WEATHER_API_KEY");
  const char *lat = getenv("WEATHER_LAT");
  const char *lon = getenv("WEATHER_LON");
  const char *lang = getenv("WEATHER_LANG");
  
  if (api_key) env_map["WEATHER_API_KEY"] = api_key;
  if (lat) env_map["WEATHER_LAT"] = lat;
  if (lon) env_map["WEATHER_LON"] = lon;
  if (lang) env_map["WEATHER_LANG"] = lang;
}

static int usage(const char *progname) {
  fprintf(stderr, "usage: %s [options]\n", progname);
  fprintf(stderr, "Displays clock and current weather on RGB matrix.\n");
  fprintf(stderr, "Options:\n");
  fprintf(stderr,
          "\t-d <time-format>  : Default '%%H:%%M'. See strftime()\n"
          "\t-f <font-file>    : Use given font.\n"
          "\t-x <x-origin>     : X-Origin of displaying text (Default: 0)\n"
          "\t-y <y-origin>     : Y-Origin of displaying text (Default: 0)\n"
          "\t-s <line-spacing> : Extra spacing between lines (Default: 2)\n"
          "\t-S <spacing>      : Extra spacing between letters (Default: 0)\n"
          "\t-C <r,g,b>        : Clock color. Default 255,255,0\n"
          "\t-W <r,g,b>        : Weather color. Default 0,255,255\n"
          "\t-B <r,g,b>        : Background-Color. Default 0,0,0\n"
          "\t-O <r,g,b>        : Outline-Color, e.g. to increase contrast.\n"
          "\t--weather-refresh <sec> : Weather refresh interval (Default: 600)\n"
          "\t--units <unit>    : Temperature units: metric, imperial, standard (Default: metric)\n"
          "\n"
          );
  rgb_matrix::PrintMatrixFlags(stderr);
  return 1;
}

static bool parseColor(Color *c, const char *str) {
  return sscanf(str, "%hhu,%hhu,%hhu", &c->r, &c->g, &c->b) == 3;
}

static bool FullSaturation(const Color &c) {
  return (c.r == 0 || c.r == 255)
    && (c.g == 0 || c.g == 255)
    && (c.b == 0 || c.b == 255);
}

int main(int argc, char *argv[]) {
  RGBMatrix::Options matrix_options;
  rgb_matrix::RuntimeOptions runtime_opt;
  if (!rgb_matrix::ParseOptionsFromFlags(&argc, &argv,
                                         &matrix_options, &runtime_opt)) {
    return usage(argv[0]);
  }

  std::vector<std::string> format_lines;
  Color clock_color(255, 255, 0);
  Color weather_color(0, 255, 255);
  Color bg_color(0, 0, 0);
  Color outline_color(0,0,0);
  bool with_outline = false;

  const char *bdf_font_file = NULL;
  int x_orig = 0;
  int y_orig = 0;
  int letter_spacing = 0;
  int line_spacing = 2;
  int weather_refresh = 600;  // 10 minutes default
  std::string units = "metric";

  int opt;
  int option_index = 0;
  static struct option long_options[] = {
    {"weather-refresh", required_argument, 0, 'r'},
    {"units", required_argument, 0, 'u'},
    {0, 0, 0, 0}
  };

  while ((opt = getopt_long(argc, argv, "x:y:f:C:W:B:O:s:S:d:r:u:", long_options, &option_index)) != -1) {
    switch (opt) {
    case 'd': format_lines.push_back(optarg); break;
    case 'x': x_orig = atoi(optarg); break;
    case 'y': y_orig = atoi(optarg); break;
    case 'f': bdf_font_file = strdup(optarg); break;
    case 's': line_spacing = atoi(optarg); break;
    case 'S': letter_spacing = atoi(optarg); break;
    case 'C':
      if (!parseColor(&clock_color, optarg)) {
        fprintf(stderr, "Invalid clock color spec: %s\n", optarg);
        return usage(argv[0]);
      }
      break;
    case 'W':
      if (!parseColor(&weather_color, optarg)) {
        fprintf(stderr, "Invalid weather color spec: %s\n", optarg);
        return usage(argv[0]);
      }
      break;
    case 'B':
      if (!parseColor(&bg_color, optarg)) {
        fprintf(stderr, "Invalid background color spec: %s\n", optarg);
        return usage(argv[0]);
      }
      break;
    case 'O':
      if (!parseColor(&outline_color, optarg)) {
        fprintf(stderr, "Invalid outline color spec: %s\n", optarg);
        return usage(argv[0]);
      }
      with_outline = true;
      break;
    case 'r': weather_refresh = atoi(optarg); break;
    case 'u': units = optarg; break;
    default:
      return usage(argv[0]);
    }
  }

  if (format_lines.empty()) {
    format_lines.push_back("%H:%M");
  }

  if (bdf_font_file == NULL) {
    fprintf(stderr, "Need to specify BDF font-file with -f\n");
    return usage(argv[0]);
  }

  // Load environment variables
  std::map<std::string, std::string> env_map;
  loadEnv(env_map);
  
  std::string api_key = env_map["WEATHER_API_KEY"];
  std::string lat_str = env_map["WEATHER_LAT"];
  std::string lon_str = env_map["WEATHER_LON"];
  std::string lang = env_map.count("WEATHER_LANG") ? env_map["WEATHER_LANG"] : "en";
  
  if (api_key.empty() || lat_str.empty() || lon_str.empty()) {
    fprintf(stderr, "Missing required environment variables: WEATHER_API_KEY, WEATHER_LAT, WEATHER_LON\n");
    fprintf(stderr, "Set them in .env file or environment\n");
    return 1;
  }
  
  double lat = atof(lat_str.c_str());
  double lon = atof(lon_str.c_str());

  // Initialize curl
  curl_global_init(CURL_GLOBAL_DEFAULT);

  /*
   * Load font. This needs to be a filename with a bdf bitmap font.
   */
  rgb_matrix::Font font;
  if (!font.LoadFont(bdf_font_file)) {
    fprintf(stderr, "Couldn't load font '%s'\n", bdf_font_file);
    curl_global_cleanup();
    return 1;
  }
  rgb_matrix::Font *outline_font = NULL;
  if (with_outline) {
    outline_font = font.CreateOutlineFont();
  }

  RGBMatrix *matrix = RGBMatrix::CreateFromOptions(matrix_options, runtime_opt);
  if (matrix == NULL) {
    curl_global_cleanup();
    return 1;
  }

  const bool all_extreme_colors = (matrix_options.brightness == 100)
    && FullSaturation(clock_color)
    && FullSaturation(weather_color)
    && FullSaturation(bg_color)
    && FullSaturation(outline_color);
  if (all_extreme_colors)
    matrix->SetPWMBits(1);

  const int x = x_orig;
  int y = y_orig;

  FrameCanvas *offscreen = matrix->CreateFrameCanvas();

  char text_buffer[256];
  char weather_buffer[128];
  struct timespec next_time;
  next_time.tv_sec = time(NULL);
  next_time.tv_nsec = 0;
  struct tm tm;
  
  time_t last_weather_fetch = 0;
  WeatherData current_weather;

  signal(SIGTERM, InterruptHandler);
  signal(SIGINT, InterruptHandler);

  while (!interrupt_received) {
    offscreen->Fill(bg_color.r, bg_color.g, bg_color.b);
    localtime_r(&next_time.tv_sec, &tm);

    // Fetch weather if needed
    if (next_time.tv_sec - last_weather_fetch >= weather_refresh) {
      current_weather = fetchWeather(api_key, lat, lon, units, lang);
      last_weather_fetch = next_time.tv_sec;
    }

    int line_offset = 0;
    
    // Draw clock line(s)
    for (const std::string &line : format_lines) {
      strftime(text_buffer, sizeof(text_buffer), line.c_str(), &tm);
      if (outline_font) {
        rgb_matrix::DrawText(offscreen, *outline_font,
                             x - 1, y + font.baseline() + line_offset,
                             outline_color, NULL, text_buffer,
                             letter_spacing - 2);
      }
      rgb_matrix::DrawText(offscreen, font,
                           x, y + font.baseline() + line_offset,
                           clock_color, NULL, text_buffer,
                           letter_spacing);
      line_offset += font.height() + line_spacing;
    }
    
    // Draw weather line
    if (current_weather.valid) {
      char temp_unit = (units == "imperial") ? 'F' : 'C';
      snprintf(weather_buffer, sizeof(weather_buffer), "%.0f%c %s",
               current_weather.temp, temp_unit, current_weather.condition_main.c_str());
      
      if (outline_font) {
        rgb_matrix::DrawText(offscreen, *outline_font,
                             x - 1, y + font.baseline() + line_offset,
                             outline_color, NULL, weather_buffer,
                             letter_spacing - 2);
      }
      rgb_matrix::DrawText(offscreen, font,
                           x, y + font.baseline() + line_offset,
                           weather_color, NULL, weather_buffer,
                           letter_spacing);
    } else {
      // Show error or loading state
      const char *status = "Loading...";
      if (outline_font) {
        rgb_matrix::DrawText(offscreen, *outline_font,
                             x - 1, y + font.baseline() + line_offset,
                             outline_color, NULL, status,
                             letter_spacing - 2);
      }
      rgb_matrix::DrawText(offscreen, font,
                           x, y + font.baseline() + line_offset,
                           weather_color, NULL, status,
                           letter_spacing);
    }

    // Wait until we're ready to show it.
    clock_nanosleep(CLOCK_REALTIME, TIMER_ABSTIME, &next_time, NULL);

    // Atomic swap with double buffer
    offscreen = matrix->SwapOnVSync(offscreen);

    next_time.tv_sec += 1;
  }

  // Finished. Shut down the RGB matrix.
  delete matrix;
  if (outline_font) delete outline_font;
  curl_global_cleanup();

  std::cout << std::endl;  // Create a fresh new line after ^C on screen
  return 0;
}


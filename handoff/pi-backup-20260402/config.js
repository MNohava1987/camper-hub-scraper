let config = {
  address: "0.0.0.0",
  port: 8080,
  basePath: "/",
  ipWhitelist: [],
  useHttps: false,
  language: "en",
  locale: "en-US",
  logLevel: ["INFO", "LOG", "WARN", "ERROR"],
  timeFormat: 12,
  units: "imperial",

  modules: [
    { module: "alert" },
    {
      module: "MMM-ImageSlideshow",
      position: "fullscreen_below",
      config: {
        imagePaths: ["modules/MMM-ImageSlideshow/photos"],
        slideshowSpeed: 15000,
        sortImagesBy: "created",
        sortImagesDescending: true,
        recursiveSubDirectories: false,
        validImageFileExtensions: "bmp,jpg,jpeg,png,gif",
        showProgressBar: false,
        transitionImages: true,
        randomizeImageOrder: false,
      }
    },
    {
      module: "clock",
      position: "top_center",
      config: { timeFormat: 12, showPeriod: true, showDate: true }
    },
    {
      module: "calendar",
      header: "Matt & Britt",
      position: "top_left",
      config: {
        maximumEntries: 6,
        maximumNumberOfDays: 14,
        calendars: [
          {
            symbol: "calendar-check",
            url: "https://calendar.google.com/calendar/ical/a8b5d884b90f15894dd9e9d84532e2c3912236c34f3a7f69e6873eefc8a68d6e%40group.calendar.google.com/private-c59cc660f84e436d9cd6c50276f2281d/basic.ics"
          }
        ]
      }
    },
    {
      module: "MMM-KampDels",
      position: "bottom_left",
      header: "Kamp Dels",
      config: {
        dataPath: "/home/mnohava/camper-hub/data/next_weekend.json",
        eventsPath: "/home/mnohava/camper-hub/data/events.json",
        updateInterval: 1800000,
        maxUpcoming: 5,
      }
    },
    {
      module: "weather",
      position: "top_right",
      header: "Waterville, MN",
      config: {
        weatherProvider: "openmeteo",
        type: "current",
        lat: 44.2219,
        lon: -93.5711,
        units: "imperial",
      }
    },
    {
      module: "weather",
      position: "top_right",
      header: "Hourly",
      config: {
        weatherProvider: "openmeteo",
        type: "hourly",
        lat: 44.2219,
        lon: -93.5711,
        units: "imperial",
        maxNumberOfHours: 6,
      }
    },
    {
      module: "weather",
      position: "top_right",
      header: "3-Day Forecast",
      config: {
        weatherProvider: "openmeteo",
        type: "forecast",
        lat: 44.2219,
        lon: -93.5711,
        units: "imperial",
        maxNumberOfDays: 3,
      }
    },
    {
      module: "MMM-CamperQR",
      position: "bottom_right",
      config: {
        codes: [
          { label: "Add Photos", image: "http://localhost:3001/qr.png" },
          { label: "Add Songs", image: "qr_spotify.png" },
        ]
      }
    }
  ]
};

/*************** DO NOT EDIT THE LINE BELOW ***************/
if (typeof module !== "undefined") { module.exports = config; }

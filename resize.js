function isInternetExplorer() {
  return navigator.userAgent.indexOf('MSIE') !== -1 || navigator.appVersion.indexOf('Trident/') > 0;
}

function setLetterbox(element, topBottom, leftRight) {
  if (isInternetExplorer()) {
    // Cannot use padding on IE11, because IE11 computes padding in addition to the size, unlike
    // other browsers, which treat padding to be part of the size.
    // e.g.
    // FF, Chrome: If CSS size = 1920x1080, padding-leftright = 460, padding-topbottomx40, then content size = (1920 - 2*460) x (1080-2*40) = 1000x1000px, and total element size = 1920x1080px.
    //       IE11: If CSS size = 1920x1080, padding-leftright = 460, padding-topbottomx40, then content size = 1920x1080px and total element size = (1920+2*460) x (1080+2*40)px.
    // IE11  treats margin like Chrome and FF treat padding.
    element.style.marginLeft = element.style.marginRight = leftRight + 'px';
    element.style.marginTop = element.style.marginBottom = topBottom + 'px';
  } else {
    // Cannot use margin to specify letterboxes in FF or Chrome, since those ignore margins in fullscreen mode.
    element.style.paddingLeft = element.style.paddingRight = leftRight + 'px';
    element.style.paddingTop = element.style.paddingBottom = topBottom + 'px';
  }
}

var inHiDPIFullscreenMode = true;
var inAspectRatioFixedFullscreenMode = true;
var inPixelPerfectFullscreenMode = false;
var inCenteredWithoutScalingFullscreenMode = false;

// In rendering performance test playback mode, we want to keep the canvas size locked on all displays 1:1 as close as possible,
// so don't upscale the canvas CSS size on large displays. I.e. a test that runs in 640x480 physical pixels canvas size would get
// zoomed in to a very large size on a 3840x2160 monitor, which would skew the pixel fillrate differences on the test depending
// on what type of display the test is run on.
// However if the test canvas size is too large to fit the display, then we do downscale, or otherwise it's quite unpleasant to
// watch the tests run (and viewer can easily conclude that the test would be broken if half of the canvas extents past the browser windw)

// In interactive mode, we do both upscale and downscale the canvas size for most convenient user experience. Hence performance
// may be different in interactive vs test modes.
var runningPerformanceTest = (location.search.indexOf('playback') != -1);
var dontUpscaleCanvasSize = (runningPerformanceTest == true);

function resizeElementToFullscreen(elem) {
  var screenWidth = inHiDPIFullscreenMode ? Math.round(window.innerWidth*window.devicePixelRatio) : window.innerWidth;
  var screenHeight = inHiDPIFullscreenMode ? Math.round(window.innerHeight*window.devicePixelRatio) : window.innerHeight;

  if (dontUpscaleCanvasSize) {
    screenWidth = Math.min(screenWidth, Module['renderTargetWidth'] || 640);
    screenHeight = Math.min(screenHeight, Module['renderTargetHeight'] || 480);
  }

  var w = screenWidth;
  var h = screenHeight;
  var canvas = elem;
  var x = canvas.width;
  var y = canvas.height;
  var topMargin;

  if (inAspectRatioFixedFullscreenMode) {
    if (w*y < x*h) h = (w * y / x) | 0;
    else if (w*y > x*h) w = (h * x / y) | 0;
    topMargin = ((screenHeight - h) / 2) | 0;
  }

  if (inHiDPIFullscreenMode) {
    topMargin /= window.devicePixelRatio;
    w /= window.devicePixelRatio;
    h /= window.devicePixelRatio;
    // Round to nearest 4 digits of precision.
    w = Math.round(w*1e4)/1e4;
    h = Math.round(h*1e4)/1e4;
    topMargin = Math.round(topMargin*1e4)/1e4;
  }

  if (inCenteredWithoutScalingFullscreenMode) {
    var t = (window.innerHeight - parseInt(canvas.style.height)) / 2;
    var b = (window.innerWidth - parseInt(canvas.style.width)) / 2;
    setLetterbox(canvas, t, b);
  } else {
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    var b = (window.innerWidth - w) / 2;
    setLetterbox(canvas, topMargin, b);
  }
}

function setElementFullscreen(elem, moveToFullscreenOnClick, inAspectRatioFixedFullscreenMode_) {
  inAspectRatioFixedFullscreenMode = inAspectRatioFixedFullscreenMode_;
  // Hide all other top level elements except the given element.
  var rootElement = elem;
  while(rootElement.parentNode && rootElement.parentNode != document.body) {
    rootElement = rootElement.parentNode;
  }
  for(var i in document.body.childNodes) {
    var child = document.body.childNodes[i];
    if (child != rootElement) {
      child.style = 'display: none';
    }
  }

  var cssWidth = window.innerWidth;
  var cssHeight = window.innerHeight;
  var rect = elem.getBoundingClientRect();
  var windowedCssWidth = rect.right - rect.left;
  var windowedCssHeight = rect.bottom - rect.top;
  var windowedRttWidth = elem.width;
  var windowedRttHeight = elem.height;

  if (inCenteredWithoutScalingFullscreenMode) {
    setLetterbox(elem, (cssHeight - windowedCssHeight) / 2, (cssWidth - windowedCssWidth) / 2);
    cssWidth = windowedCssWidth;
    cssHeight = windowedCssHeight;
  } else if (inAspectRatioFixedFullscreenMode) {
    if (cssWidth*windowedRttHeight < windowedRttWidth*cssHeight) {
      var desiredCssHeight = windowedRttHeight * cssWidth / windowedRttWidth;
      setLetterbox(elem, (cssHeight - desiredCssHeight) / 2, 0);
      cssHeight = desiredCssHeight;
    } else {
      var desiredCssWidth = windowedRttWidth * cssHeight / windowedRttHeight;
      setLetterbox(elem, 0, (cssWidth - desiredCssWidth) / 2);
      cssWidth = desiredCssWidth;
    }
  }

  // If we are adding padding, must choose a background color or otherwise Chrome will give the
  // padding a default white color. Do it only if user has not customized their own background color.
  if (!elem.style.backgroundColor) elem.style.backgroundColor = 'black';
  // IE11 does the same, but requires the color to be set in the document body.
  if (!document.body.style.backgroundColor) document.body.style.backgroundColor = 'black'; // IE11
  // Firefox always shows black letterboxes independent of style color.

  elem.style.width = cssWidth + 'px';
  elem.style.height = cssHeight + 'px';

  // Downscale with best performance.
  elem.style.imageRendering = 'optimizeSpeed';
  elem.style.imageRendering = '-moz-crisp-edges';
  elem.style.imageRendering = '-o-crisp-edges';
  elem.style.imageRendering = '-webkit-optimize-contrast';
  elem.style.imageRendering = 'optimize-contrast';
  elem.style.imageRendering = 'crisp-edges';
  elem.style.imageRendering = 'pixelated';

  var dpiScale = inHiDPIFullscreenMode ? window.devicePixelRatio : 1;

  document.documentElement.style.overflow = 'hidden';  // Firefox, Chrome
  document.body.scroll = "no"; // IE11
  document.body.style.margin = '0px'; // Override default document margin area on all browsers.

  function resize() {
    resizeElementToFullscreen(elem);
  }
  resize();
  window.addEventListener('resize', resize);

  if (moveToFullscreenOnClick) {
    elem.addEventListener('click', function() {
      elem.requestFullscreen();
    });
    elem.addEventListener('touchstart', function() {
      elem.requestFullscreen();
    });
  }
}

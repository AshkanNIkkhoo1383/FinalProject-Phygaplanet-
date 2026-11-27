(function () {
  const audio = document.getElementById("global-audio");
  if (!audio) return;
  const title = document.getElementById("player-title");
  const artist = document.getElementById("player-artist");

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  document.addEventListener("click", async (event) => {
    const button = event.target.closest(".js-play-song");
    if (!button) return;
    const url = button.dataset.audioUrl;
    if (!url) return;
    if (audio.src !== new URL(url, window.location.href).href) audio.src = url;
    title.textContent = button.dataset.title || "در حال پخش";
    artist.textContent = button.dataset.artist || "PhygaPlanet";
    try {
      await audio.play();
      const playUrl = button.dataset.playUrl;
      if (playUrl) {
        fetch(playUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "X-CSRFToken": (document.querySelector('meta[name="csrf-token"]') || {}).content || getCookie("csrftoken"),
            "X-Requested-With": "XMLHttpRequest"
          }
        }).catch(() => {});
      }
    } catch (error) {
      title.textContent = "پخش انجام نشد؛ فایل صوتی را بررسی کن.";
    }
  });
})();

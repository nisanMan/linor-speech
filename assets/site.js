// תפריט המבורגר בטלפון
var menuBtn = document.querySelector(".menu-btn");
menuBtn.addEventListener("click", function () {
  var open = menuBtn.getAttribute("aria-expanded") !== "true";
  menuBtn.setAttribute("aria-expanded", open);
  document.body.classList.toggle("menu-open", open);
});

// הגדלת תמונות תעודה
var box = document.querySelector(".lightbox");
document.querySelectorAll("a.zoom").forEach(function (a) {
  a.addEventListener("click", function (e) {
    if (!box.showModal) return;
    e.preventDefault();
    box.querySelector("img").src = a.href;
    box.showModal();
  });
});
box.addEventListener("click", function () { box.close(); });

// מעקב לחיצות ב-Google Analytics: וואטסאפ, טלפון, וייז, פייסבוק, מייל
function contactMethod(href) {
  if (href.indexOf("wa.me") > -1) return "whatsapp";
  if (href.indexOf("tel:") === 0) return "phone";
  if (href.indexOf("waze.com") > -1) return "waze";
  if (href.indexOf("facebook.com") > -1) return "facebook";
  if (href.indexOf("mailto:") === 0) return "email";
  return null;
}
document.addEventListener("click", function (e) {
  var a = e.target.closest("a");
  if (!a || typeof gtag !== "function") return;
  var method = contactMethod(a.getAttribute("href") || "");
  if (!method) return;
  var where = a.classList.contains("float-wa") || a.classList.contains("float-waze") ? "floating_button"
            : a.classList.contains("btn") ? "home_button"
            : a.closest(".contact") ? "contact_page"
            : a.closest(".site-footer") ? "footer" : "text_link";
  gtag("event", "contact_click", { method: method, location: where });
});

for (const button of document.querySelectorAll("[data-show-field]")) {
  const input = document.getElementById(button.dataset.showField);
  const label = input.labels[0].textContent.toLowerCase();
  button.hidden = false;
  button.addEventListener("click", () => {
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    button.textContent = show ? "Hide" : "Show";
    button.setAttribute("aria-label", button.textContent + " " + label);
  });
}

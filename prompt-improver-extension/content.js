// Detect visible text inputs and textareas
function getInputBoxes() {
  return [
    ...document.querySelectorAll("textarea, input[type='text']")
  ].filter(el => el.offsetParent !== null); // visible
}

// Create floating improve button near input box
function createImproveButton(input) {
  if (input.dataset.improveBtnAttached === "true") return;
  input.dataset.improveBtnAttached = "true";

  const btn = document.createElement("button");
  btn.textContent = "✨ Improve";
  btn.style.position = "absolute";
  btn.style.zIndex = 9999;
  btn.style.padding = "4px 10px";
  btn.style.fontSize = "12px";
  btn.style.borderRadius = "6px";
  btn.style.border = "none";
  btn.style.backgroundColor = "#10a37f";
  btn.style.color = "#fff";
  btn.style.cursor = "pointer";
  btn.style.boxShadow = "0 2px 6px rgba(0,0,0,0.2)";

  // position button above input box
  const rect = input.getBoundingClientRect();
  btn.style.top = (window.scrollY + rect.top - 30) + "px";
  btn.style.left = (window.scrollX + rect.left) + "px";
  btn.style.position = "absolute";

  document.body.appendChild(btn);

  // Ensure only one fetch call per click
  btn.disabled = false;

  btn.addEventListener("click", () => {
    if (btn.disabled) return;
    btn.disabled = true;
    btn.textContent = "⏳ Improving...";

    const textValue = input.value;
    if (!textValue) {
      alert("Input box is empty.");
      btn.disabled = false;
      btn.textContent = "✨ Improve";
      return;
    }

    fetch("http://localhost:5000/improve", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({prompt: textValue}),
    })
      .then(response => {
        if (!response.ok) throw new Error(`Server responded with ${response.status}`);
        return response.json();
      })
      .then(data => {
        if (data.improved) {
          input.value = data.improved;
          input.dispatchEvent(new Event("input", {bubbles: true}));
        } else {
          alert("No improved text received.");
        }
      })
      .catch(error => alert("Error improving prompt: " + error.message))
      .finally(() => {
        btn.disabled = false;
        btn.textContent = "✨ Improve";
      });
  });
}

// Monitor DOM changes and add buttons to new inputs
const observer = new MutationObserver(() => {
  getInputBoxes().forEach(createImproveButton);
});
observer.observe(document.body, {childList: true, subtree: true});

// Add buttons on page load
getInputBoxes().forEach(createImproveButton);

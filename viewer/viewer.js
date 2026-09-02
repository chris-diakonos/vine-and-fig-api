(async function loadViewer() {
  const viewer = document.getElementById("model-viewer");
  const artifactLabel = document.getElementById("artifact-label");
  const structureHash = document.getElementById("structure-hash");
  const downloadLink = document.getElementById("download-link");
  const bomLink = document.getElementById("bom-link");
  const errorMessage = document.getElementById("error-message");

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.hidden = false;
    artifactLabel.textContent = "Unable to load model";
  }

  try {
    const response = await fetch("./manifest.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Manifest request failed with ${response.status}`);
    }

    const manifest = await response.json();
    const glbUrl = manifest?.artifacts?.glb?.url;
    const bomUrl = manifest?.artifacts?.bom?.url;

    if (!glbUrl) {
      throw new Error("Manifest does not include artifacts.glb.url");
    }

    viewer.src = glbUrl;
    downloadLink.href = glbUrl;
    if (bomUrl) {
      bomLink.href = bomUrl;
    }

    const hash = manifest.structure_hash || "unknown";
    artifactLabel.textContent = `Artifact ${hash}`;
    structureHash.textContent = `Structure hash: ${hash}`;
  } catch (error) {
    showError(error.message || "Could not load manifest");
  }
})();

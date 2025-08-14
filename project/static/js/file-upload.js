document.addEventListener("DOMContentLoaded", function() {
  // Get references to the elements
  const uploadArea = document.getElementById("uploadArea");
  if (!uploadArea) return; // Only run on pages with upload area

  // Use the correct file input ID from your Django form
  const fileInput = document.getElementById("id_document") || document.getElementById("fileInput");
  if (!fileInput) return;

  const browseButton = uploadArea.querySelector(".btn-secondary-glass");
  const uploadForm = document.getElementById("uploadForm") || document.querySelector("form.paper-form");

  // Handle browse button click
  if (browseButton) {
    browseButton.addEventListener("click", function(e) {
      e.preventDefault();
      fileInput.click(); // Trigger the hidden file input
    });
  }

  // Handle file selection
  fileInput.addEventListener("change", function() {
    if (fileInput.files.length > 0) {
      // Display the selected file name
      const fileName = fileInput.files[0].name;
      uploadArea.querySelector("h6").textContent = "Selected file:";
      uploadArea.querySelector("p").textContent = fileName;

      // Change the icon to indicate file is selected
      const icon = uploadArea.querySelector(".fa-cloud-upload-alt, .fa-file-alt");
      if (icon) icon.className = "fas fa-file-alt fa-3x text-glass-muted mb-3";
    }
  });

  // Handle drag and drop functionality
  uploadArea.addEventListener("dragover", function(e) {
    e.preventDefault();
    uploadArea.classList.add("dragover");
  });

  uploadArea.addEventListener("dragleave", function() {
    uploadArea.classList.remove("dragover");
  });

  uploadArea.addEventListener("drop", function(e) {
    e.preventDefault();
    uploadArea.classList.remove("dragover");

    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      const fileName = e.dataTransfer.files[0].name;
      uploadArea.querySelector("h6").textContent = "Selected file:";
      uploadArea.querySelector("p").textContent = fileName;
      const icon = uploadArea.querySelector(".fa-cloud-upload-alt, .fa-file-alt");
      if (icon) icon.className = "fas fa-file-alt fa-3x text-glass-muted mb-3";
    }
  });

  // Handle form submission with loading state
  if (uploadForm) {
    uploadForm.addEventListener("submit", function(e) {
      e.preventDefault();

      // Validate inputs
      const titleInput = uploadForm.querySelector('input[name="title"]');
      const categoryInput = uploadForm.querySelector('select[name="category"]');
      const title = titleInput ? titleInput.value : "";
      const category = categoryInput ? categoryInput.value : "";

      if (!title) {
        alert("Please enter a paper title");
        return;
      }

      if (!category) {
        alert("Please select a category");
        return;
      }

      if (fileInput.files.length === 0) {
        alert("Please select a file to upload");
        return;
      }

      // Show loading state on the button
      const submitButton = uploadForm.querySelector('button[type="submit"]');
      showLoading(submitButton, "Uploading...");

      // Create FormData and submit
      const formData = new FormData(uploadForm);

      fetch(uploadForm.action, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(response => response.json())
      .then(data => {
        // Reset loading state
        hideLoading(submitButton);

        if (data.success) {
          // Show success message
          alert(data.message);

          // Reset the form
          uploadForm.reset();
          uploadArea.querySelector("h6").textContent = "Drag & Drop your paper here";
          uploadArea.querySelector("p").textContent = "or click to browse files";
          const icon = uploadArea.querySelector(".fa-file-alt, .fa-cloud-upload-alt");
          if (icon) icon.className = "fas fa-cloud-upload-alt fa-3x text-glass-muted mb-3";
        } else {
          // Show error message
          alert(data.message || "An error occurred while uploading the file");
        }
      })
      .catch(error => {
        hideLoading(submitButton);
        alert("An error occurred: " + error.message);
      });
    });
  }

  // Helper function to show loading state
  function showLoading(buttonElement, loadingText = "Loading...") {
    if (!buttonElement) return;
    const originalText = buttonElement.innerHTML;
    buttonElement.setAttribute('data-original-text', originalText);
    buttonElement.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${loadingText}`;
    buttonElement.disabled = true;
    buttonElement.classList.add('loading');
  }

  // Helper function to hide loading state
  function hideLoading(buttonElement) {
    if (!buttonElement || !buttonElement.hasAttribute('data-original-text')) return;
    const originalText = buttonElement.getAttribute('data-original-text');
    buttonElement.innerHTML = originalText;
    buttonElement.disabled = false;
    buttonElement.classList.remove('loading');
  }
});
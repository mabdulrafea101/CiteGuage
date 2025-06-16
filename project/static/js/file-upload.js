document.addEventListener("DOMContentLoaded", function() {
  // Get references to the elements
  const uploadArea = document.getElementById("uploadArea");
  const fileInput = document.getElementById("fileInput");
  const browseButton = uploadArea.querySelector(".btn-secondary-glass");
  const uploadForm = document.getElementById("uploadForm");
  
  // Handle browse button click
  browseButton.addEventListener("click", function(e) {
    e.preventDefault();
    fileInput.click(); // Trigger the hidden file input
  });
  
  // Handle file selection
  fileInput.addEventListener("change", function() {
    if (fileInput.files.length > 0) {
      // Display the selected file name
      const fileName = fileInput.files[0].name;
      uploadArea.querySelector("h6").textContent = "Selected file:";
      uploadArea.querySelector("p").textContent = fileName;
      
      // Change the icon to indicate file is selected
      uploadArea.querySelector(".fa-cloud-upload-alt").className = "fas fa-file-alt fa-3x text-glass-muted mb-3";
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
      uploadArea.querySelector(".fa-cloud-upload-alt").className = "fas fa-file-alt fa-3x text-glass-muted mb-3";
    }
  });
  
  // Handle form submission with loading state
  uploadForm.addEventListener("submit", function(e) {
    e.preventDefault();
    
    // Validate inputs
    const title = document.querySelector('input[name="title"]').value;
    const category = document.querySelector('select[name="category"]').value;
    
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
        uploadArea.querySelector(".fa-file-alt").className = "fas fa-cloud-upload-alt fa-3x text-glass-muted mb-3";
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
  
  // Helper function to hide loading state
  function hideLoading(buttonElement) {
    if (!buttonElement || !buttonElement.hasAttribute('data-original-text')) return;
    
    const originalText = buttonElement.getAttribute('data-original-text');
    buttonElement.innerHTML = originalText;
    buttonElement.disabled = false;
    buttonElement.classList.remove('loading');
  }
});
$(document).ready(function() {
  // Handle form submission
  $('#uploadform').on('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const submitBtn = $('#submit');
    
    // Disable button during processing
    submitBtn.prop('disabled', true);
    submitBtn.text('PROCESSING...');
    
    $.ajax({
      url: '/predict',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(response) {
        // Update the result section
        if (response.prediction === "No banana detected") {
          $('#resultClassType').text(response.prediction).addClass('no-banana');
          $('#confidenceValue').text('N/A');
        } else {
          $('#resultClassType').text(response.prediction).removeClass('no-banana');
          $('#confidenceValue').text((response.confidence * 100).toFixed(2) + '%');
        }
        
        // Update the preview image
        if (response.image_url) {
          $('#previewImage').attr('src', response.image_url).show();
          $('#placeholderText').hide();
        }
        
        // Show the result container with animation
        $('.result-container').hide().slideDown(300);
        
        // Scroll to results
        $('html, body').animate({
          scrollTop: $('.result-container').offset().top - 100
        }, 500);
      },
      error: function(xhr) {
        let errorMsg = "Error processing image. Please try again.";
        if (xhr.responseJSON && xhr.responseJSON.error) {
          errorMsg = xhr.responseJSON.error;
        }
        alert(errorMsg);
      },
      complete: function() {
        // Re-enable button
        submitBtn.prop('disabled', false);
        submitBtn.text('CLASSIFY IMAGE');
      }
    });
  });
});
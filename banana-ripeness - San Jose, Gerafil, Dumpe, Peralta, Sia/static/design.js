function openCamera() {
  $('#cameraModal').show();
  video = document.getElementById('video');
  canvas = document.getElementById('canvas');
  context = canvas.getContext('2d');

  navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } })
    .then(stream => {
      video.srcObject = stream;
    })
    .catch(err => {
      alert("Camera Error: " + err);
    });
}

function closeCamera() {
  $('#cameraModal').hide();
  if (video.srcObject) {
    video.srcObject.getTracks().forEach(track => track.stop());
    video.srcObject = null;
  }
}

function takeSnapshot() {
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  context.drawImage(video, 0, 0);
  
  const imageDataUrl = canvas.toDataURL('image/png');
  $('#previewImage').attr('src', imageDataUrl).show();
  $('#placeholderText').hide();
  
  closeCamera();
}

function readURL(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    
    reader.onload = function(e) {
      $('#previewImage').attr('src', e.target.result).show();
      $('#placeholderText').hide();
    }
    
    reader.readAsDataURL(input.files[0]);
  }
}

function readURL(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    
    reader.onload = function(e) {
      $('#previewImage').attr('src', e.target.result).show();
      $('#placeholderText').hide();
    }
    
    reader.readAsDataURL(input.files[0]);
  }
}

$(document).ready(function() {
  // Handle touch events for better mobile interaction
  if ('ontouchstart' in window) {
    // Make buttons more touch-friendly
    $('button').css({
      'padding': '16px 32px',
      'min-width': '120px'
    });
    
    // Prevent double-tap zoom
    document.addEventListener('dblclick', function(e) {
      e.preventDefault();
    }, { passive: false });
    
    // Add touch feedback
    $('button').on('touchstart', function() {
      $(this).addClass('button-touch');
    }).on('touchend', function() {
      $(this).removeClass('button-touch');
    });
  }
});
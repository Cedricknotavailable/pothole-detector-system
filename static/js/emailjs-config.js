// EmailJS Configuration
// Update these values to match your EmailJS account settings

const EMAILJS_CONFIG = {
  publicKey: 'dXcaIv5LGMTpybpw2',
  serviceId: 'service_cs9uath',
  templateId: 'template_ai1brni'  // UPDATE THIS with your correct template ID
};

// Initialize EmailJS
(function(){
  emailjs.init(EMAILJS_CONFIG.publicKey);
})();


// =================================== // STYLE.JS -
// Glassmorphism Framework 
// =================================== // 
// Initialize when DOM is loaded 
document.addEventListener('DOMContentLoaded', function() {
initializeGlassmorphism(); }); // Main initialization function function
initializeGlassmorphism() { initializeParticles(); initializeFormEffects();
initializeAnimations(); initializeUtilities(); } // ===== PARTICLE SYSTEM =====
function initializeParticles() { const particles =
document.querySelectorAll('.particle'); particles.forEach((particle, index) => {
// Add hover effects particle.addEventListener('mouseenter', function() {
this.style.transform = 'scale(1.2)'; this.style.opacity = '1'; });
particle.addEventListener('mouseleave', function() { this.style.transform =
'scale(1)'; this.style.opacity = '0.7'; }); // Add random movement variation
particle.addEventListener('animationiteration', function() { const randomOffset
= Math.random() * 10 - 5; this.style.left = `calc(${this.style.left ||
getComputedStyle(this).left} + ${randomOffset}px)`; }); }); } // ===== FORM
EFFECTS ===== function initializeFormEffects() { // Form input hover and focus
effects document.querySelectorAll('.form-control').forEach(input => {
input.addEventListener('focus', function() { const container =
this.closest('.form-floating, .input-group'); if (container) {
container.style.transform = 'translateY(-2px)'; } });
input.addEventListener('blur', function() { const container =
this.closest('.form-floating, .input-group'); if (container) {
container.style.transform = 'translateY(0)'; } }); // Add typing effect
input.addEventListener('input', function() { if (this.value.length > 0) {
this.style.background = 'rgba(255, 255, 255, 0.15)'; } else {
this.style.background = 'rgba(255, 255, 255, 0.1)'; } }); }); // Button hover
effects document.querySelectorAll('.btn-primary-glass, .btn-secondary-glass,
.btn-login, .btn-signup').forEach(btn => { btn.addEventListener('mouseenter',
function() { this.style.transform = 'translateY(-2px) scale(1.02)'; });
btn.addEventListener('mouseleave', function() { this.style.transform =
'translateY(0) scale(1)'; }); }); } // ===== ANIMATIONS ===== function
initializeAnimations() { // Intersection Observer for scroll animations const
observerOptions = { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }; const
observer = new IntersectionObserver(function(entries) { entries.forEach(entry =>
{ if (entry.isIntersecting) { entry.target.classList.add('animate__animated',
'animate__fadeInUp'); } }); }, observerOptions); // Observe elements that need
scroll animations document.querySelectorAll('.glass-card-small, .content-area >
*').forEach(el => { observer.observe(el); }); } // ===== PASSWORD UTILITIES
===== function togglePassword(fieldId, iconId) { const passwordInput =
document.getElementById(fieldId); const toggleIcon =
document.getElementById(iconId); if (!passwordInput || !toggleIcon) return; if
(passwordInput.type === 'password') { passwordInput.type = 'text';
toggleIcon.className = 'fas fa-eye-slash'; } else { passwordInput.type =
'password'; toggleIcon.className = 'fas fa-eye'; } // Add animation feedback
toggleIcon.style.transform = 'scale(1.2)'; setTimeout(() => {
toggleIcon.style.transform = 'scale(1)'; }, 150); } function
checkPasswordStrength(passwordId = 'password', strengthBarId = 'strengthBar') {
const password = document.getElementById(passwordId)?.value || ''; const
strengthBar = document.getElementById(strengthBarId); if (!strengthBar) return;
let strength = 0; // Check password criteria if (password.length >= 8)
strength++; if (password.match(/[a-z]/)) strength++; if
(password.match(/[A-Z]/)) strength++; if (password.match(/[0-9]/)) strength++;
if (password.match(/[^a-zA-Z0-9]/)) strength++; // Update strength bar const
widthPercent = (strength / 5) * 100; strengthBar.style.width = widthPercent +
'%'; // Update strength class strengthBar.className = 'password-strength-bar';
if (strength <= 2) { strengthBar.classList.add('strength-weak'); } else if
(strength <= 4) { strengthBar.classList.add('strength-medium'); } else {
strengthBar.classList.add('strength-strong'); } return strength; } function
checkPasswordMatch(passwordId = 'password', confirmPasswordId =
'confirmPassword', matchIndicatorId = 'passwordMatch') { const password =
document.getElementById(passwordId)?.value || ''; const confirmPassword =
document.getElementById(confirmPasswordId)?.value || ''; const matchIndicator =
document.getElementById(matchIndicatorId); if (!matchIndicator) return; if
(confirmPassword === '') { matchIndicator.textContent = '';
matchIndicator.className = 'password-match'; return; } if (password ===
confirmPassword) { matchIndicator.textContent = '✓ Passwords match';
matchIndicator.className = 'password-match match-success'; return true; } else {
matchIndicator.textContent = '✗ Passwords do not match';
matchIndicator.className = 'password-match match-error'; return false; } } 
// ===== LOADING STATES ===== 

function showLoading(buttonElement, loadingText = 'Loading...') { 
    if (!buttonElement) return; const originalText =
buttonElement.innerHTML; buttonElement.setAttribute('data-original-text',
originalText); buttonElement.innerHTML = `<i
  class="fas fa-spinner fa-spin me-2"
></i
>${loadingText}`; buttonElement.disabled = true;
buttonElement.classList.add('loading'); } 

function hideLoading(buttonElement) {
if (!buttonElement) return; const originalText =
buttonElement.getAttribute('data-original-text'); 
if (originalText) {
buttonElement.innerHTML = originalText; } buttonElement.disabled = false;
buttonElement.classList.remove('loading'); } // ===== FORM VALIDATION =====

function validateForm(formElement) { if (!formElement) return false; const
inputs = formElement.querySelectorAll('input[required]'); let isValid = true;
inputs.forEach(input => { if (!input.value.trim()) { input.style.borderColor =
'#ff4757'; input.style.boxShadow = '0 0 0 0.25rem rgba(255, 71, 87, 0.25)';
isValid = false; // Reset styles after 3 seconds setTimeout(() => {
input.style.borderColor = ''; input.style.boxShadow = ''; }, 3000); } }); return
isValid; } // ===== NOTIFICATION SYSTEM ===== function showNotification(message,
type = 'info', duration = 3000) { const notification =
document.createElement('div'); notification.className = `notification
notification-${type} animate__animated animate__fadeInDown`;
notification.innerHTML = `
<div class="notification-content">
  <i class="fas fa-${getNotificationIcon(type)} me-2"></i>
  ${message}
</div>
`; // Add notification styles notification.style.cssText = ` position: fixed;
top: 20px; right: 20px; background: rgba(255, 255, 255, 0.15); backdrop-filter:
blur(20px); border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.2);
color: white; padding: 15px 20px; z-index: 9999; max-width: 300px; box-shadow: 0
10px 25px rgba(0, 0, 0, 0.1); `; document.body.appendChild(notification); //
Auto remove setTimeout(() => {
notification.classList.remove('animate__fadeInDown');
notification.classList.add('animate__fadeOutUp'); setTimeout(() => {
document.body.removeChild(notification); }, 300); }, duration); } function
getNotificationIcon(type) { switch(type) { case 'success': return
'check-circle'; case 'error': return 'exclamation-circle'; case 'warning':
return 'exclamation-triangle'; default: return 'info-circle'; } } // =====
UTILITY FUNCTIONS ===== function initializeUtilities() { // Add smooth scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
anchor.addEventListener('click', function (e) { e.preventDefault(); const target
= document.querySelector(this.getAttribute('href')); if (target) {
target.scrollIntoView({ behavior: 'smooth', block: 'start' }); } }); }); // Add
ripple effect to buttons document.querySelectorAll('.btn-primary-glass,
.btn-secondary-glass').forEach(btn => { btn.addEventListener('click',
createRipple); }); } function createRipple(event) { const button =
event.currentTarget; const ripple = document.createElement('span');
ripple.className = 'ripple'; button.appendChild(ripple); }

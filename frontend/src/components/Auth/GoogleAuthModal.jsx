import React, { useState, useEffect } from 'react';
import { X, Eye, EyeOff } from 'lucide-react';

export function GoogleAuthModal({ isOpen, onClose, onLoginSuccess, initialMode = 'login' }) {
  const [internalMode, setInternalMode] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const mode = internalMode || initialMode;

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Enter an email address');
      return;
    }
    if (!password.trim()) {
      setError('Enter a password');
      return;
    }

    setIsLoading(true);
    setError('');

    setTimeout(() => {
      setIsLoading(false);
      const user = {
        name: name.trim() || email.split('@')[0],
        email: email.trim(),
        avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80'
      };
      onLoginSuccess(user);
    }, 700);
  };

  const handleGoogleOneTap = () => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      const user = {
        name: 'Alex Rivera',
        email: 'alex.rivera@gmail.com',
        avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80'
      };
      onLoginSuccess(user);
    }, 600);
  };

  return (
    <div 
      className="google-auth-backdrop" 
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div 
        className="google-auth-card" 
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button 
          type="button" 
          className="google-auth-close-btn" 
          onClick={onClose}
          title="Close (Esc)"
        >
          <X size={18} />
        </button>

        {/* Google Multi-Color Logo */}
        <div className="google-logo-wrapper">
          <svg viewBox="0 0 48 48" width="40" height="40">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
          </svg>
        </div>

        {/* Header Titles */}
        <h1 className="google-auth-title">
          {mode === 'login' ? 'Sign in' : 'Create an Account'}
        </h1>
        <p className="google-auth-subtitle">
          to continue to <span className="app-brand-name">DiagramGPT</span>
        </p>

        {/* 1-Click Google OAuth Pill */}
        <button
          type="button"
          className="google-one-click-btn"
          onClick={handleGoogleOneTap}
          disabled={isLoading}
        >
          <div className="google-g-mini">
            <svg viewBox="0 0 48 48" width="18" height="18">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            </svg>
          </div>
          <span>Continue with Google</span>
        </button>

        <div className="google-auth-divider">
          <span>or use email</span>
        </div>

        {/* Form Inputs */}
        <form onSubmit={handleSubmit} className="google-auth-form">
          {mode === 'signup' && (
            <div className="google-input-group">
              <input
                type="text"
                className="google-text-input"
                placeholder=" "
                value={name}
                onChange={(e) => setName(e.target.value)}
                id="google-name"
                disabled={isLoading}
              />
              <label htmlFor="google-name" className="google-floating-label">First name</label>
            </div>
          )}

          <div className="google-input-group">
            <input
              type="email"
              className={`google-text-input ${error ? 'has-error' : ''}`}
              placeholder=" "
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (error) setError('');
              }}
              id="google-email"
              disabled={isLoading}
            />
            <label htmlFor="google-email" className="google-floating-label">Email or phone</label>
          </div>

          <div className="google-input-group password-group">
            <input
              type={showPassword ? 'text' : 'password'}
              className="google-text-input"
              placeholder=" "
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              id="google-password"
              disabled={isLoading}
            />
            <label htmlFor="google-password" className="google-floating-label">
              {mode === 'login' ? 'Enter your password' : 'Create password'}
            </label>
            <button
              type="button"
              className="google-toggle-pw"
              onClick={() => setShowPassword((prev) => !prev)}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          {error && <div className="google-auth-error">{error}</div>}

          {/* Links & Submit Actions */}
          <div className="google-auth-actions">
            <button
              type="button"
              className="google-text-btn"
              onClick={() => {
                setInternalMode(mode === 'login' ? 'signup' : 'login');
                setError('');
              }}
            >
              {mode === 'login' ? 'Create account' : 'Sign in instead'}
            </button>

            <button
              type="submit"
              className="google-submit-btn"
              disabled={isLoading}
            >
              {isLoading ? 'Signing in...' : (mode === 'login' ? 'Next' : 'Create')}
            </button>
          </div>
        </form>

        {/* Footer info */}
        <div className="google-auth-footer">
          <span>Protected by DiagramGPT Academic Authentication</span>
        </div>
      </div>
    </div>
  );
}

export default GoogleAuthModal;

"""
Custom middleware for Zero-Bot API.
Handles logging, authentication, and security.
"""

import json
import time
import uuid
import logging
from datetime import datetime
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('zero_bot')


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware to log all API requests and responses."""
    
    def process_request(self, request):
        """Log incoming request details."""
        request.start_time = time.time()
        request.request_id = str(uuid.uuid4())
        
        # Log request details
        logger.info(f"[{request.request_id}] {request.method} {request.path}")
        
        # Log request body for POST/PUT requests (excluding sensitive data)
        if request.method in ['POST', 'PUT', 'PATCH'] and request.content_type == 'application/json':
            try:
                body = json.loads(request.body.decode('utf-8'))
                # Remove sensitive fields
                safe_body = {k: v for k, v in body.items() if k not in ['password', 'token', 'secret']}
                logger.debug(f"[{request.request_id}] Request body: {safe_body}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                logger.debug(f"[{request.request_id}] Non-JSON request body")
    
    def process_response(self, request, response):
        """Log response details and timing."""
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            logger.info(
                f"[{getattr(request, 'request_id', 'unknown')}] "
                f"Response: {response.status_code} ({duration:.3f}s)"
            )
        
        # Add request ID to response headers
        if hasattr(request, 'request_id'):
            response['X-Request-ID'] = request.request_id
        
        return response


# DataIsolationMiddleware and EconomicValidationMiddleware will be recreated
# in the new dual-chain architecture


class CORSMiddleware(MiddlewareMixin):
    """Custom CORS middleware for Zero-Bot API."""
    
    def process_response(self, request, response):
        """Add CORS headers to response."""
        
        # Add CORS headers for API endpoints
        if request.path.startswith('/api/'):
            response['Access-Control-Allow-Origin'] = '*'  # Configure properly for production
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response['Access-Control-Max-Age'] = '86400'
        
        return response
    
    def process_request(self, request):
        """Handle preflight OPTIONS requests."""
        if request.method == 'OPTIONS' and request.path.startswith('/api/'):
            response = JsonResponse({'status': 'ok'})
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response['Access-Control-Max-Age'] = '86400'
            return response
        
        return None


class ErrorHandlingMiddleware(MiddlewareMixin):
    """Middleware for standardized error handling."""
    
    def process_exception(self, request, exception):
        """Handle uncaught exceptions with standardized error response."""
        
        # Log the exception
        logger.error(
            f"[{getattr(request, 'request_id', 'unknown')}] "
            f"Unhandled exception: {type(exception).__name__}: {exception}",
            exc_info=True
        )
        
        # Return standardized error response for API endpoints
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'internal_server_error',
                'message': 'An internal server error occurred',
                'timestamp': datetime.utcnow().isoformat(),
                'request_id': getattr(request, 'request_id', 'unknown')
            }, status=500)
        
        # Let Django handle non-API exceptions normally
        return None


class RateLimitingMiddleware(MiddlewareMixin):
    """Simple rate limiting middleware for Zero-Bot API."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = {}  # In production, use Redis
        super().__init__(get_response)
    
    def process_request(self, request):
        """Apply rate limiting based on IP address."""
        
        # Skip rate limiting for health checks
        if request.path in ['/health/', '/validate-rules/']:
            return None
        
        # Skip rate limiting in development
        from django.conf import settings
        if getattr(settings, 'DEBUG', False):
            return None
        
        # Get client IP
        client_ip = self.get_client_ip(request)
        current_time = int(time.time())
        
        # Initialize or update request count
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        # Remove old requests (older than 1 minute)
        self.request_counts[client_ip] = [
            req_time for req_time in self.request_counts[client_ip]
            if current_time - req_time < 60
        ]
        
        # Check rate limit (60 requests per minute)
        if len(self.request_counts[client_ip]) >= 60:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JsonResponse({
                'error': 'rate_limit_exceeded',
                'message': 'Rate limit exceeded. Please try again later.',
                'timestamp': datetime.utcnow().isoformat(),
                'request_id': getattr(request, 'request_id', 'unknown')
            }, status=429)
        
        # Add current request
        self.request_counts[client_ip].append(current_time)
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Middleware to add security headers."""
    
    def process_response(self, request, response):
        """Add security headers to response."""
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add CSP header for API endpoints
        if request.path.startswith('/api/'):
            response['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none';"
        
        return response


class TelegramWebhookAuthMiddleware(MiddlewareMixin):
    """Middleware to authenticate Telegram webhook requests."""
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Validate Telegram webhook authentication."""
        
        # Only apply to webhook endpoints
        if not request.path.startswith('/webhooks/telegram/'):
            return None
        
        # Skip authentication in development
        from django.conf import settings
        if getattr(settings, 'DEBUG', False):
            return None
        
        # TODO: Implement Telegram webhook signature validation
        # This would validate the X-Telegram-Bot-Api-Secret-Token header
        # against the bot's webhook secret
        
        return None 
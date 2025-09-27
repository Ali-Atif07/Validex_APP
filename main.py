

# Modified Flask app for production deployment
from captcha_handler import automate_foscos_with_captcha
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import uuid
from datetime import datetime
import threading
import time
from werkzeug.utils import secure_filename
import logging

# Configure logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["*"])  # Configure CORS for mobile app

# Production configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    UPLOAD_FOLDER = '/tmp/uploads'  # Use /tmp for cloud platforms
    RESULTS_FOLDER = '/tmp/results'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # API Keys from environment
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    CAPTCHA_API_KEY = os.environ.get('CAPTCHA_API_KEY')

app.config.from_object(Config)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Global session storage (use Redis in production for multiple servers)
sessions_store = {}

class ProductionSessionManager:
    def __init__(self):
        self.sessions = sessions_store
    
    def create_session(self, data):
        session_id = str(uuid.uuid4())
        session_data = {
            'sessionId': session_id,
            'status': 'initializing',
            'progress': 0,
            'startTime': datetime.now().isoformat(),
            'logs': [],
            'result': None,
            'error': None,
            **data
        }
        self.sessions[session_id] = session_data
        return session_data
    
    def update_session(self, session_id, **kwargs):
        if session_id in self.sessions:
            self.sessions[session_id].update(kwargs)
            # Add timestamp for last update
            self.sessions[session_id]['lastUpdated'] = datetime.now().isoformat()
        return self.sessions.get(session_id)
    
    def get_session(self, session_id):
        return self.sessions.get(session_id)
    
    def cleanup_old_sessions(self):
        """Remove sessions older than 24 hours"""
        cutoff_time = datetime.now().timestamp() - (24 * 60 * 60)
        to_remove = []
        
        for session_id, session in self.sessions.items():
            session_time = datetime.fromisoformat(session['startTime']).timestamp()
            if session_time < cutoff_time:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.sessions[session_id]
            
        logger.info(f"Cleaned up {len(to_remove)} old sessions")

session_manager = ProductionSessionManager()

# Import your scraping functions
try:
    from foscos_scraper import extract_license_with_llm, automate_foscos_form
    SCRAPING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Scraping modules not available: {e}")
    SCRAPING_AVAILABLE = False

def run_scraping_process(session_id, license_number, url=None):
    """Background scraping process"""
    try:
        if not SCRAPING_AVAILABLE:
            raise Exception("Scraping modules not available")
        
        logger.info(f"Starting scraping for session {session_id}")
        session_manager.update_session(session_id, status='running', progress=10)
        
        # Extract license if URL provided
        if url:
            session_manager.update_session(session_id, status='extracting_license', progress=20)
            license_result = extract_license_with_llm(url)
            
            if not license_result.get('license_number'):
                raise Exception('Could not extract license number from URL')
            
            license_number = license_result['license_number']
        
        # Run FoSCoS automation
        session_manager.update_session(session_id, status='running_foscos', progress=40)
        foscos_result = automate_foscos_form(license_number)
        
        # Process results
        session_manager.update_session(session_id, status='processing_results', progress=80)
        
        final_result = {
            'extraction_timestamp': datetime.now().isoformat(),
            'license_number': license_number,
            'url': url,
            'search_results': foscos_result.get('license_search_results', []),
            'product_details': foscos_result.get('product_details'),
            'summary': {
                'search_successful': len(foscos_result.get('license_search_results', [])) > 0,
                'total_records': len(foscos_result.get('license_search_results', [])),
                'products_found': bool(foscos_result.get('product_details'))
            }
        }
        
        # Save result
        result_filename = f"result_{session_id[:8]}_{int(time.time())}.json"
        result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
        
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)
        
        # Update session
        session_manager.update_session(
            session_id,
            status='completed',
            progress=100,
            result=final_result,
            result_filename=result_filename
        )
        
        logger.info(f"Scraping completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"Scraping failed for session {session_id}: {str(e)}")
        session_manager.update_session(
            session_id,
            status='error',
            error=str(e),
            progress=100
        )

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'scraping_available': SCRAPING_AVAILABLE,
        'active_sessions': len(session_manager.sessions)
    })



# Flask routes for CAPTCHA handling
@app.route('/api/scrape', methods=['POST'])
def start_scraping():
    """Start scraping with CAPTCHA support"""
    try:
        data = request.get_json()
        license_number = data.get('license_number')
        url = data.get('url')
        
        if not license_number and not url:
            return jsonify({'error': 'License number or URL required'}), 400
        
        # Create session
        session = session_manager.create_session({
            'license_number': license_number,
            'url': url
        })
        
        # Start background process
        thread = threading.Thread(
            target=automate_foscos_with_captcha,
            args=(session['sessionId'], license_number)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'sessionId': session['sessionId'],
            'status': 'started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/scrape', methods=['POST'])
def start_scraping():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        license_number = data.get('license_number')
        url = data.get('url')
        
        if not license_number and not url:
            return jsonify({'error': 'License number or URL required'}), 400
        
        # Create session
        session = session_manager.create_session({
            'license_number': license_number,
            'url': url
        })
        
        # Start background process
        thread = threading.Thread(
            target=run_scraping_process,
            args=(session['sessionId'], license_number, url)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'sessionId': session['sessionId'],
            'status': 'started',
            'message': 'Scraping process initiated'
        })
        
    except Exception as e:
        logger.error(f"Error starting scraping: {str(e)}")
        return jsonify({'error': str(e)}), 500



@app.route('/api/captcha-image/<session_id>', methods=['GET'])
def get_captcha_image(session_id):
    """Get CAPTCHA image for a session"""
    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    if session.get('captcha_image'):
        return jsonify({
            'captcha_image': session['captcha_image'],
            'timestamp': session.get('captcha_timestamp')
        })
    else:
        return jsonify({'error': 'No CAPTCHA available'}), 404
    

@app.route('/api/submit-captcha/<session_id>', methods=['POST'])
def submit_captcha_solution(session_id):
    """Receive CAPTCHA solution from mobile app"""
    try:
        data = request.get_json()
        solution = data.get('solution', '').strip()
        
        if not solution:
            return jsonify({'error': 'CAPTCHA solution required'}), 400
        
        success = session_manager.submit_captcha_solution(session_id, solution)
        
        if success:
            return jsonify({
                'message': 'CAPTCHA solution received',
                'status': 'processing'
            })
        else:
            return jsonify({'error': 'Session not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# @app.route('/api/status/<session_id>', methods=['GET'])
# def get_session_status(session_id):
#     session = session_manager.get_session(session_id)
#     if not session:
#         return jsonify({'error': 'Session not found'}), 404
    
#     return jsonify(session)
@app.route('/api/status/<session_id>', methods=['GET'])
def get_session_status(session_id):
    """Get session status including CAPTCHA state"""
    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Return session data (including captcha_image if pending)
    response_data = {
        'sessionId': session['sessionId'],
        'status': session['status'],
        'progress': session['progress'],
        'captcha_pending': session.get('captcha_pending', False),
    }
    
    # Include CAPTCHA image if pending
    if session.get('captcha_pending') and session.get('captcha_image'):
        response_data['captcha_image'] = session['captcha_image']
    
    # Include result if completed
    if session.get('result'):
        response_data['result'] = session['result']
    
    # Include error if failed
    if session.get('error'):
        response_data['error'] = session['error']
    
    return jsonify(response_data)


@app.route('/api/results', methods=['GET'])
def get_all_results():
    try:
        results = []
        results_folder = app.config['RESULTS_FOLDER']
        
        for filename in os.listdir(results_folder):
            if filename.endswith('.json'):
                filepath = os.path.join(results_folder, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Create summary for list view
                    summary = {
                        'filename': filename,
                        'license_number': data.get('license_number'),
                        'company_name': None,
                        'status': None,
                        'created_at': data.get('extraction_timestamp'),
                        'total_records': data.get('summary', {}).get('total_records', 0)
                    }
                    
                    # Get company info from first search result
                    if data.get('search_results'):
                        first_result = data['search_results'][0]
                        summary['company_name'] = first_result.get('company_name')
                        summary['status'] = first_result.get('status')
                    
                    results.append(summary)
                    
                except Exception as e:
                    logger.warning(f"Error reading {filename}: {e}")
                    continue
        
        # Sort by creation time (newest first)
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({'files': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/results/<filename>', methods=['GET'])
def get_result_details(filename):
    try:
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config['RESULTS_FOLDER'], safe_filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Result not found'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Cleanup task - run periodically
def cleanup_task():
    while True:
        try:
            session_manager.cleanup_old_sessions()
            time.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
            time.sleep(3600)

# Start cleanup task
cleanup_thread = threading.Thread(target=cleanup_task)
cleanup_thread.daemon = True
cleanup_thread.start()

# Production WSGI server configuration
if __name__ == '__main__':
    # Development server
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
else:
    # Production server (gunicorn)
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
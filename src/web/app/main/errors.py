from flask import render_template, request, jsonify
from . import main
from .. import csrf


@csrf.error_handler
def csrf_error(reason=None):
    return render_template('csrf_error.html', reason=reason), 400


@main.app_errorhandler(404)
def not_found(reason=None):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return render_template('404.html', reason=reason), 404


@main.app_errorhandler(403)
def forbidden(reason=None):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    return render_template('403.html', reason=reason), 403


@main.app_errorhandler(500)
def internal_error(reason=None):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'internal server error'})
        response.status_code = 500
        return response
    return render_template('500.html', reason=reason), 500


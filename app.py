import os
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Register blueprints
    from services.matriculas import bp as matriculas_bp
    from services.health import bp as health_bp
    from services.courses import bp as courses_bp
    from services.years_suap import bp as years_suap_bp
    from services.studentbycities import bp as studentbycities_bp
    from services.enrollments import bp as enrollments_bp
    from services.analysis import bp as analysis_bp
    from services.analytics_behavour import bp as analytics_behavour_bp
    from services.polos import bp as polos_bp
    from services.campus import bp as campus_bp
    from services.conclusoes_ano import bp as conclusoes_ano_bp

    app.register_blueprint(matriculas_bp)      # /matriculas
    app.register_blueprint(health_bp)          # /health
    app.register_blueprint(courses_bp)         # /courses
    app.register_blueprint(years_suap_bp)      # /years_suap
    app.register_blueprint(studentbycities_bp) # /studentbycities
    app.register_blueprint(enrollments_bp)     # /enrollments
    app.register_blueprint(analysis_bp)        # /analysis
    app.register_blueprint(analytics_behavour_bp)  # /analytics_behavour
    app.register_blueprint(polos_bp)           # /polos
    app.register_blueprint(campus_bp)          # /campus
    app.register_blueprint(conclusoes_ano_bp, name="conclusoes_ano", url_prefix="/conclusoes_ano")  # /conclusoes_ano

    return app

# Expose the app for Gunicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

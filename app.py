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
    from services.poloChart import polo_chart_bp # Blueprint do poloChart   


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
    app.register_blueprint(polo_chart_bp) #polo_char_bp registrado
  
    return app

# Expose the app for Gunicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


# vv ----- ADD THIS ENTIRE BLOCK FOR DEBUGGING ----- vv
@app.cli.command("list-routes")
def list_routes():
    """List all available routes."""
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = f"[{arg}]"
        
        methods = ','.join(rule.methods)
        url = urllib.parse.unquote(rule.endpoint)
        line = f"{url:50s} {methods:20s} {rule.rule}"
        output.append(line)
    
    print("\n--- Registered Routes ---")
    for line in sorted(output):
        print(line)
    print("-------------------------\n")
# ^^ -------------------------------------------------- ^^
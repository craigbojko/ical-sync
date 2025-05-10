from invoke import task

@task
def install(c):
    """Install the project in editable mode with development dependencies."""
    c.run("pip install -r requirements.txt")
    
@task
def dev(c):
    """Run the app in watch mode with development dependencies."""
    c.run("PYTHONPATH=src watchmedo shell-command \
        --patterns='src/*.py' \
        --ignore-directories \
        --recursive \
        --verbose \
        --command='clear && python src/main.py' \
    ")

@task
def test(c):
    """Run tests using pytest with verbose output."""
    c.run("PYTHONPATH=src pytest -v \
        --md-report \
        --cov=src \
        --cov-report=term \
        --cov-report=html:coverage \
        --cov-report=xml:coverage/coverage.xml \
    ")

@task
def watch(c):
    """Watch for file changes and run pytest automatically (using pytest-watch), clearing console each time."""
    c.run("PYTHONPATH=src ptw -c -v -- \
        -v \
        --md-report \
        --cov=src \
        --cov-report=term \
        --cov-report=html:coverage \
        --cov-report=xml:coverage/coverage.xml \
    ", pty=True)

@task
def lint(c):
    """Check code style with ruff."""
    c.run("ruff check .")

@task
def format(c):
    """Format code using ruff."""
    c.run("ruff format .")

@task
def clean(c):
    """Remove __pycache__ and *.pyc files."""
    c.run("find . -type d -name '__pycache__' -exec rm -r {} +")
    c.run("find . -type f -name '*.pyc' -delete")

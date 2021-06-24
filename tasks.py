from shutil import rmtree, copy, move

from invoke import task


@task
def clean(c):
    rmtree('build', ignore_errors=True)
    rmtree('dist', ignore_errors=True)


@task
def install_dependencies(c):
    c.run('poetry install')


@task
def test(c):
    c.run('poetry run coverage erase && cd tests && poetry run coverage erase')
    c.run('cd tests && poetry run coverage run manage.py test')
    c.run('cd tests && poetry run coverage xml -i')
    move('tests/.coverage', '.coverage')
    move('tests/coverage.xml', 'coverage.xml')
    c.run('poetry run coverage report -m')


@task
def build(c):
    clean(c)
    install_dependencies(c)
    test(c)
    c.run('poetry build')


@task
def quality_gate(c, runner_home='$SONAR_RUNNER_HOME', name='${name}', sonar_url='http://sonar.riachuelo.net:8080'):
    c.run('%s/bin/sonar-scanner '
          '-Dsonar.sources=./vox_message '
          '-Dsonar.projectKey=%s '
          '-Dsonar.projectName=%s '
          '-Dsonar.projectDescription="" '
          '-Dsonar.projectVersion=${baseVersion} '
          '-Dsonar.exclusions="build/*,dist/*,vox_message.egg-info/*,setup.py,*.xml,*.md,**/tests.py" '
          '-Dsonar.inclusions="**/*.py" '
          '-Dsonar.scm.exclusions.disabled=true '
          '-Dsonar.host.url=%s '
          '-Dsonar.python.coverage.reportPaths=coverage.xml '
          '-Dsonar.coverage.exclusions="build/*,dist/*,vox_message.egg-info/*,setup.py,*.xml,*.md,**/tests.py"'
          % (runner_home, name, name, sonar_url))


@task
def deploy(c, repo_name='pypi'):
    c.run('poetry publish')
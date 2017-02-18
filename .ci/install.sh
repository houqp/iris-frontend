#!/bin/bash
CI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${CI_DIR}/common.sh"

sudo pip install virtualenvwrapper
. /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv iris-frontend
workon iris-frontend

pushd ${TRAVIS_BUILD_DIR}
python setup.py develop
pip install -r dev_requirements.txt
popd

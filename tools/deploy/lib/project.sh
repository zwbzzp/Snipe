#!/bin/bash
# Install project

set -e

SOURCE_TYPE=${SOURCE_TYPE:-"local"}
PROJECT_NAME=${PROJECT_NAME:-"phoenix"}
DEST_DIR=${DEST_DIR:-"/srv/www/vinzor"}
LOG_DIR=${LOG_DIR:-"/var/log/vinzor"}

CURRENT_DIR=$(cd "$(dirname "$0")"; pwd)
ARCHIVES_DIR=$(cd "$CURRENT_DIR/../archives/$(lsb_release -rs)"; pwd)
PYTHON_ARCHIVES=$(cd "${ARCHIVES_DIR}/python"; pwd)
SOURCE_DIR=$(cd "${ARCHIVES_DIR}/project"; pwd)
CONF_DIR=$(cd "${CURRENT_DIR}/../conf"; pwd)

# install pip3
apt-get $APT_OPTIONS -y --force-yes install python3-pip

# install virtualenv
if [ "${SOURCE_TYPE}" == "local" ]; then
    pip3 install --no-index --find-links=file:///${PYTHON_ARCHIVES} virtualenv
else
    pip3 install virtualenv
fi

rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

# active virtualenv
virtualenv -p python3 "$DEST_DIR/venv"
source "$DEST_DIR/venv/bin/activate"

# copy project and uwsgi.ini to destination folder
cp -aL "$SOURCE_DIR" "$DEST_DIR"
mv -f "$DEST_DIR/project" "$DEST_DIR/$PROJECT_NAME"
cp -f "$CONF_DIR/mgmt_uwsgi.ini" "$DEST_DIR/$PROJECT_NAME"

mkdir -p /var/log/uwsgi

# configure uwsgi.ini
cfg="$DEST_DIR/$PROJECT_NAME/mgmt_uwsgi.ini"
crudini --set --existing $cfg uwsgi base "${DEST_DIR}"
#crudini --set --existing $cfg uwsgi socket "${DEST_DIR}/%n.sock"
crudini --set --existing $cfg uwsgi logto "/var/log/uwsgi/%n.log"

# create link of uwsgi.ini in vassals. vassals will be used by uwsgi.conf
mkdir -p /etc/uwsgi/vassals
ln -sf "$DEST_DIR/$PROJECT_NAME/mgmt_uwsgi.ini" /etc/uwsgi/vassals

# copy upstart scripts to ubuntu upstart
cp -f "$CONF_DIR"/upstart/* /etc/init

# install python requirements
if [ $SOURCE_TYPE == "local" ]; then
    pip3 install --no-index --find-links=file:///${PYTHON_ARCHIVES} uwsgi
    pip3 install --no-index --find-links=file:///${PYTHON_ARCHIVES} --upgrade setuptools
    pip3 install --no-index --find-links=file:///${PYTHON_ARCHIVES} pbr
    pip3 install --no-index --find-links=file:///${PYTHON_ARCHIVES} -r ${DEST_DIR}/${PROJECT_NAME}/requirements.txt
else
    pip3 install uwsgi
    pip3 install -r ${DEST_DIR}/${PROJECT_NAME}/requirements.txt
fi

# flask config
FLASK_CONFIG=${FLASK_CONFIG:-"product"}
OS_AUTH_URL=${OS_AUTH_URL:-"http://172.18.215.3:5000/v2.0"}
OS_TENANT_NAME=${OS_TENANT_NAME:-"demo"}
OS_USERNAME=${OS_USERNAME:-"demo"}
OS_PASSWORD=${OS_PASSWORD:-"admin123"}
CELERY_BROKER_URL=${CELERY_BROKER_URL:-"amqp://guest:guest@127.0.0.1:5672"}
CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-"db+sqlite:///${DEST_DIR}/${PROJECT_NAME}/celery-result.sqlite"}

sed -e "s|FLASK_CONFIG=.*|FLASK_CONFIG=${FLASK_CONFIG}|g" \
    -e "s|OS_AUTH_URL=.*|OS_AUTH_URL=${OS_AUTH_URL}|g" \
    -e "s|OS_TENANT_NAME=.*|OS_TENANT_NAME=${OS_TENANT_NAME}|g" \
    -e "s|OS_USERNAME=.*|OS_USERNAME=${OS_USERNAME}|g" \
    -e "s|OS_PASSWORD=.*|OS_PASSWORD=${OS_PASSWORD}|g" \
    -e "s|CELERY_BROKER_URL=.*|CELERY_BROKER_URL=${CELERY_BROKER_URL}|g" \
    -e "s|CELERY_RESULT_BACKEND=.*|CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}|g" \
    -e "s|SQLALCHEMY_DATABASE_URI=.*|SQLALCHEMY_DATABASE_URI=${SQLALCHEMY_DATABASE_URI}|g" \
    -e "s|GANGLIA_URL=.*|GANGLIA_URL=${GANGLIA_URL}|g" \
    -i ${DEST_DIR}/${PROJECT_NAME}/src/web/.env

# log config
mkdir -p /var/log/vinzor
cfg="${DEST_DIR}/${PROJECT_NAME}/src/web/logging.ini"
crudini --set $cfg logger_root handlers fileHandler
crudini --set --existing $cfg handler_fileHandler args "('${LOG_DIR}/all.log','midnight',1,5,'utf-8',)"
crudini --set $cfg logger_celery handlers celeryFileHandler
crudini --set --existing $cfg handler_celeryFileHandler args "('${LOG_DIR}/celery.log','midnight',1,5,'utf-8',)"
cfg="${DEST_DIR}/${PROJECT_NAME}/src/etc/phoenix.ini"
crudini --set --existing $cfg database connection "$SQLALCHEMY_DATABASE_URI"
crudini --set --existing $cfg openstack auth_url "$OS_AUTH_URL"
crudini --set --existing $cfg openstack tenant "$OS_TENANT_NAME"
crudini --set --existing $cfg openstack username "$OS_TENANT_NAME"
crudini --set --existing $cfg openstack password "$OS_PASSWORD"

# create database
mysql -u"${MYSQL_USER}" -p"${MYSQL_PASS}" -e \
    'CREATE DATABASE IF NOT EXISTS phoenix default character set utf8 COLLATE utf8_general_ci'
cd ${DEST_DIR}/${PROJECT_NAME}/src/web
python ${DEST_DIR}/${PROJECT_NAME}/src/web/manage.py db upgrade
python ${DEST_DIR}/${PROJECT_NAME}/src/web/manage.py deploy

function deamon() {
    process=$1
    if (status ${process} | grep stop > /dev/null) ; then
        start ${process}
    else
        restart ${process}
    fi
    echo process ${process} started
}

deamon vinzor-beat
deamon vinzor-worker
deamon vinzor-uwsgi

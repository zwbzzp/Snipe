#!/usr/bin/env bash

set -e

CURRENT_DIR=$(cd "$(dirname "$0")"; pwd)
ROOT_DIR=$(cd "$CURRENT_DIR"/..; pwd)

OS_VERSION=$(lsb_release -rs)
ARCHIVES_DIR=$(cd "$ROOT_DIR"/archives/"$OS_VERSION"; pwd)

LOCALRC="$ROOT_DIR/localrc"
SOURCE_TYPE=${SOURCE_TYPE:-local}
echo && echo "Load configurations"
source "$LOCALRC"

TMP_SOURCES_LIST=$(mktemp)
cat $CURRENT_DIR/sources-$SOURCE_TYPE-$(lsb_release -rs).list > "$TMP_SOURCES_LIST"
sed -e "s|%PACKAGE_DIR%|$ARCHIVES_DIR/ubuntu|" \
    -i "$TMP_SOURCES_LIST"
export APT_OPTIONS="-o Dir::Etc::SourceList=$TMP_SOURCES_LIST
 -o Dir::Etc::SourceParts=$CURRENT_DIR/sources.list.d"
sudo apt-get $APT_OPTIONS -y --force-yes update
sudo apt-get $APT_OPTIONS -y --force-yes install git

sudo rm -rf "${ARCHIVES_DIR}/project"
mkdir -p "${ARCHIVES_DIR}/project"
PROJECT_DIR=$(cd "${ARCHIVES_DIR}/project"; pwd)
REPO_URL="ssh://git@172.18.231.4:2222/vinzor/phoenix.git"
REPO_KEY=${REPO_KEY:-${CURRENT_DIR}/phoenix}
REPO_BRANCH=${REPO_BRANCH:-"develop"}

chmod 400 "$REPO_KEY"

ssh-agent bash -c "ssh-add \"$REPO_KEY\"; git clone --depth 1 -b \"$REPO_BRANCH\" \"$REPO_URL\" \"$PROJECT_DIR\""

# compile
for pyfile in $(find "$PROJECT_DIR" -type f -name '*.py'); do
    python3 -OO -m py_compile "$pyfile"
    if !(echo "$pyfile" | grep manage.py > /dev/null); then
        rm -f pyfile
    fi
done

echo 'Done'
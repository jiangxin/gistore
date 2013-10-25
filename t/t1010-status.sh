#!/bin/sh
#
# Copyright (c) 2013 Jiang Xin
#

test_description='Test gistore status'

TEST_NO_CREATE_REPO=NoThanks
. ./lib-worktree.sh
. ./test-lib.sh

cwd=$(pwd -P)

cat >expect << EOF
root/doc
root/src
EOF

# Parent .gitignore ignore all this directory, and new file
# will not show in git-status.
test_expect_success 'remove to avoid .gitignore side-effect' '
	if [ -f "$TEST_DIRECTORY/.gitignore" ]; then
		mv  "$TEST_DIRECTORY/.gitignore" "$TEST_DIRECTORY/.gitignore.save"
	fi
'

test_expect_success 'status show backup list' '
	prepare_work_tree &&
	gistore init --repo repo.git &&
	gistore add --repo repo.git root/src &&
	gistore add --repo repo.git root/doc &&
	gistore status --repo repo.git --backup \
		| sed -e "s#^${cwd}/##g" > actual &&
	test_cmp expect actual
'

# Before git v1.7.4,  filenames in git-status are NOT quoted.
# So strip double quote before compare with this.
cat >expect << EOF
 M root/doc/COPYRIGHT
 M root/src/README.txt
 D root/src/images/test-binary-1.png
 D root/src/lib/b/baz.a
?? root/src/lib/a/foo.h
EOF

test_expect_success GIT_CAP_WILDMATCH 'status --git (1)' '
	gistore commit --repo repo.git && \
	echo "hack" >> root/doc/COPYRIGHT && \
	echo "hack" >> root/src/README.txt && \
	touch root/src/lib/a/foo.h && \
	rm root/src/images/test-binary-1.png && \
	rm root/src/lib/b/baz.a && \
	gistore status --repo repo.git --git -s \
		| sed -e "s#${cwd#/}/##g" | sed -e "s/\"//g" > actual &&
	test_cmp expect actual
'

# Rstore parent .gitignore file
test_expect_success 'restore .gitignore' '
	if [ -f "$TEST_DIRECTORY/.gitignore.save" ]; then
		mv  "$TEST_DIRECTORY/.gitignore.save" "$TEST_DIRECTORY/.gitignore"
	fi
'

cat >expect <<EOF
Error: Can not find repo at "non-exist-repo.git"
EOF

test_expect_success 'fail for non-exist gitstore repo' '
	test_must_fail gistore status --repo non-exist-repo.git &&
	(gistore add --repo non-exist-repo.git 2>actual || true) &&
	test_cmp expect actual
'

cat >expect <<EOF
Error: Failure while executing: git status --bad-git-status-option
EOF

test_expect_success 'fail for bad git status options' '
	test_must_fail gistore status --repo repo.git --bad-git-status-option &&
	(gistore status --repo repo.git --bad-git-status-option 2>&1 | grep "^Error" |
	 sed -e "s/ [^ ]*\/git/ git/" > actual || true) &&
	test_cmp expect actual
'

test_done

#!/bin/sh
#
# Copyright (c) 2013 Jiang Xin
#

test_description='Test gistore add and rm'

TEST_NO_CREATE_REPO=NoThanks
. ./lib-worktree.sh
. ./test-lib.sh

cwd=$(pwd -P)

cat >expect << EOF
$cwd/root/doc
$cwd/root/src
EOF

test_expect_success 'repo initial with blank backup list' '
	gistore init --repo repo.git &&
	gistore status --repo repo.git --backup | sed -e /^$/d | > actual &&
	test ! -s actual
'

test_expect_success 'add root/src and root/doc' '
	gistore add --repo repo.git root/src &&
	gistore add --repo repo.git root/doc &&
	gistore status --repo repo.git --backup >actual &&
	test_cmp expect actual
'

cat >expect << EOF
$cwd/root/src
EOF

test_expect_success 'remove root/doc' '
	(
		cd repo.git &&
		gistore rm ../root/doc &&
		gistore status --backup >../actual
	) && test_cmp expect actual
'

cat >expect << EOF
$cwd/root
EOF

test_expect_success 'root override root/src and root/doc' '
	gistore add --repo repo.git root/src &&
	gistore add --repo repo.git root &&
	gistore add --repo repo.git root/doc &&
	gistore status --repo repo.git --backup > actual &&
	test_cmp expect actual
'

test_expect_success 'not add parent of repo' '
	gistore add --repo repo.git .. &&
	gistore add --repo repo.git . &&
	gistore status --repo repo.git --backup > actual &&
	test_cmp expect actual
'

test_expect_success 'not add subdir of repo' '
	gistore add --repo repo.git repo.git &&
	gistore add --repo repo.git repo.git/objects &&
	gistore add --repo repo.git repo.git/refs &&
	gistore status --repo repo.git --backup > actual &&
	test_cmp expect actual
'

cat >expect <<EOF
Error: Can not find repo at "non-exist-repo.git"
EOF

test_expect_success 'fail to add/remove on non-exist repo' '
	test_must_fail gistore add --repo non-exist-repo.git root/src &&
	(gistore add --repo non-exist-repo.git 2>actual || true) &&
	test_cmp expect actual &&
	test_must_fail gistore rm --repo non-exist-repo.git root/src &&
	(gistore add --repo non-exist-repo.git 2>actual || true) &&
	test_cmp expect actual
'

test_expect_success 'fail if no argument for add/remove' '
	test_must_fail gistore add --repo repo.git &&
	test_must_fail gistore rm --repo repo.git
'

test_done

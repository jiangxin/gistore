#!/bin/sh
#
# Copyright (c) 2013 Jiang Xin
#

test_description='Test gistore commit'

TEST_NO_CREATE_REPO=NoThanks
. ./lib-worktree.sh
. ./test-lib.sh

do_hack()
{
	echo "hack $*" >> root/src/README.txt
	echo "hack $*" >> root/doc/COPYRIGHT
}

cwd=$(pwd -P)
n=0

test_expect_success 'initialize for commit' '
	n=$((n+1)) &&
	prepare_work_tree &&
	gistore init --repo repo.git &&
	gistore config --repo repo.git full_backup_number 3 &&
	gistore config --repo repo.git increment_backup_number 5 &&
	gistore add --repo repo.git root/src &&
	gistore add --repo repo.git root/doc &&
	gistore commit --repo repo.git -m "Backup No. $n" &&
	test "$(count_git_commits repo.git)" = "$n"
'

cat >expect << EOF
Backup No. 6
Backup No. 5
Backup No. 4
Backup No. 3
Backup No. 2
Backup No. 1
EOF

test_expect_success 'no rotate when commit 5 times' '
	i=0 &&
	while test $i -lt 5; do
		i=$((i+1));
		n=$((n+1));
		do_hack $n;
		gistore commit --repo repo.git -m "Backup No. $n";
	done &&
	git_log_only_subject repo.git > actual &&
	test_cmp expect actual &&
	echo "* master" > expect &&
	gistore repo repo.git branch > actual &&
	test_cmp expect actual
'

cat >expect <<EOF
  gistore/1
* master
EOF

test_expect_success 'rotate with additional commit' '
	n=$((n+1)) && do_hack $n &&
	gistore commit --repo repo.git -m "Backup No. $n" &&
	gistore repo repo.git branch > actual &&
	test_cmp expect actual
'

cat >expect << EOF
Backup No. 7
Full backup of repo.git
Backup No. 5
Backup No. 4
Backup No. 3
Backup No. 2
Backup No. 1
EOF

test_expect_success 'graft test' '
	git_log_only_subject repo.git > actual &&
	test_cmp expect actual &&
	head -2 expect > expect2 &&
	git_log_only_subject repo.git --without_grafts > actual &&
	test_cmp expect2 actual &&
	echo "Backup No. 6" >  expect3 &&
	tail -5 expect       >> expect3 &&
	git_log_only_subject repo.git --without_grafts gistore/1 > actual &&
	test_cmp expect3 actual
'

cat >expect << EOF
Backup No. 12
Full backup of repo.git
Backup No. 10
Backup No. 9
Backup No. 8
Backup No. 7
Full backup of repo.git
Backup No. 5
Backup No. 4
Backup No. 3
Backup No. 2
Backup No. 1
EOF

test_expect_success 'rotate after commit another 5 times' '
	i=0 &&
	while test $i -lt 5; do
		i=$((i+1));
		n=$((n+1));
		do_hack $n;
		gistore commit --repo repo.git -m "Backup No. $n";
	done &&
	git_log_only_subject repo.git > actual &&
	test_cmp expect actual &&
	echo "  gistore/1" >  expect &&
	echo "  gistore/2" >> expect &&
	echo "* master"    >> expect &&
	gistore repo repo.git branch > actual &&
	test_cmp expect actual
'

cat >expect << EOF
Backup No. 12
Full backup of repo.git
EOF

test_expect_success 'commit log of master (no grafts)' '
	git_log_only_subject repo.git --without_grafts > actual &&
	test_cmp expect actual
'

cat >expect << EOF
Backup No. 11
Backup No. 10
Backup No. 9
Backup No. 8
Backup No. 7
Full backup of repo.git
EOF

test_expect_success 'commit log of gistore/1 (no grafts)' '
	git_log_only_subject repo.git --without_grafts gistore/1 > actual &&
	test_cmp expect actual
'

cat >expect << EOF
Backup No. 6
Backup No. 5
Backup No. 4
Backup No. 3
Backup No. 2
Backup No. 1
EOF

test_expect_success 'commit log of gistore/2 (no grafts)' '
	git_log_only_subject repo.git --without_grafts gistore/2 > actual &&
	test_cmp expect actual
'

cat >expect << EOF
  gistore/1
  gistore/2
  gistore/3
* master
EOF

test_expect_success 'after 20 commits' '
	i=0 &&
	while test $i -lt 20; do
		i=$((i+1));
		n=$((n+1));
		do_hack $n;
		gistore commit --repo repo.git -m "Backup No. $n";
	done &&
	gistore repo repo.git branch > actual &&
	test_cmp expect actual
'

cat >expect << EOF
Backup No. 21
Backup No. 20
Backup No. 19
Backup No. 18
Backup No. 17
Full backup of repo.git
EOF

test_expect_success 'commit log of gistore/3 (no grafts)' '
	git_log_only_subject repo.git --without_grafts gistore/3 > actual &&
	test_cmp expect actual
'

cat >expect << EOF
Backup No. 26
Backup No. 25
Backup No. 24
Backup No. 23
Backup No. 22
Full backup of repo.git
EOF

test_expect_success 'commit log of gistore/2 (no grafts)' '
	git_log_only_subject repo.git --without_grafts gistore/2 > actual &&
	test_cmp expect actual
'

cat >expect << EOF
Backup No. 31
Backup No. 30
Backup No. 29
Backup No. 28
Backup No. 27
Full backup of repo.git
EOF

test_expect_success 'commit log of gistore/1 (no grafts)' '
	git_log_only_subject repo.git --without_grafts gistore/1 > actual &&
	test_cmp expect actual
'

cat >expect << EOF
Backup No. 32
Full backup of repo.git
EOF

test_expect_success 'commit log of master (no grafts)' '
	git_log_only_subject repo.git --without_grafts > actual &&
	test_cmp expect actual
'

cat >expect << EOF
Backup No. 32
Full backup of repo.git
Backup No. 30
Backup No. 29
Backup No. 28
Backup No. 27
Full backup of repo.git
Backup No. 25
Backup No. 24
Backup No. 23
Backup No. 22
Full backup of repo.git
Backup No. 20
Backup No. 19
Backup No. 18
Backup No. 17
Full backup of repo.git
EOF

test_expect_success 'commit log of master (with grafts)' '
	git_log_only_subject repo.git > actual &&
	test_cmp expect actual
'

test_expect_success 'purge history using gc' '
	count=$(count_git_objects repo.git) &&
	gistore repo repo.git prune --expire=now &&
	gistore repo repo.git gc &&
	test $(count_git_objects repo.git) -eq $count &&
	gistore gc --repo repo.git --force &&
	test $(count_git_objects repo.git) -lt $count
'

test_done

#!/bin/sh
#
# Copyright (c) 2013 Jiang Xin
#

test_description='Test gistore task'

TEST_NO_CREATE_REPO=NoThanks
. ./lib-worktree.sh
. ./test-lib.sh

do_hack()
{
	echo "hack $*" >> root/src/README.txt
	echo "hack $*" >> root/doc/COPYRIGHT
}

cwd=$(pwd -P)

HOME=$cwd
unset XDG_CONFIG_HOME
GISTORE_TEST_GIT_CONFIG=Yes
export HOME XDG_CONFIG_HOME GISTORE_TEST_GIT_CONFIG

touch config_file
GIT_CONFIG=$cwd/config_file
export GIT_CONFIG

cat >expect << EOF
System level Tasks
User level Tasks
EOF

test_expect_success 'initial config' '
	prepare_work_tree &&
	gistore init --repo repo1.git &&
	gistore init --repo repo2.git &&
	gistore add  --repo repo1.git root/src root/doc &&
	gistore add  --repo repo2.git root/src root/doc &&
	gistore task list |sed -e "/^$/d" > actual &&
	test_cmp expect actual
'

# Ruby hash to yaml may have different order, so sort before compare.
cat >expect << EOF
    hello => repo1.git
    world => repo2.git
System level Tasks
User level Tasks
EOF

test_expect_success 'task add and task list' '
	gistore task add hello repo1.git &&
	gistore task add world repo2.git &&
	gistore task list | grep -q "$cwd" &&
	gistore task list | sed -e "/^$/d" | \
		sed -e "s#${cwd}/##g" | sort -u > actual &&
	test_cmp expect actual
'

test_expect_success 'commit specific task' '
	test "$(count_git_commits repo1.git)" = "0" &&
	test "$(count_git_commits repo2.git)" = "0" &&
	gistore commit --repo hello -m "task hello, commit no.1" &&
	test "$(count_git_commits repo1.git)" = "1" &&
	test "$(count_git_commits repo2.git)" = "0" &&
	gistore ci     --repo world -m "for world, commit no.1" &&
	test "$(count_git_commits repo1.git)" = "1" &&
	test "$(count_git_commits repo2.git)" = "1" &&
	test "$(git_log_only_subject repo1.git -1)" = \
		"task hello, commit no.1" &&
	test "$(git_log_only_subject repo2.git -1)" = \
		"for world, commit no.1"
'

test_expect_success 'commit all task' '
	do_hack &&
	gistore commit-all &&
	test "$(count_git_commits repo1.git)" = "2" &&
	test "$(count_git_commits repo2.git)" = "2" &&
	do_hack &&
	gistore ci-all -m "commit invoke by ci-all" &&
	test "$(count_git_commits repo1.git)" = "3" &&
	test "$(count_git_commits repo2.git)" = "3" &&
	test "$(git_log_only_subject repo1.git -1)" = \
		"commit invoke by ci-all" &&
	test "$(git_log_only_subject repo2.git -1)" = \
		"commit invoke by ci-all"
'

cat >expect << EOF
System level Tasks
    hello => repo1.git
User level Tasks
    hello => repo1.git
EOF

test_expect_success 'task remove' '
	do_hack &&
	gistore task rm world &&
	gistore task list |sed -e "/^$/d" | sed -e "s#${cwd}/##g" > actual &&
	test_cmp expect actual &&
	gistore commit-all &&
	test "$(count_git_commits repo1.git)" = "4" &&
	test "$(count_git_commits repo2.git)" = "3"
'

cat >expect << EOF
    hello => repo1.git
    world => repo2.git
System level Tasks
User level Tasks
EOF

test_expect_success 'commit-all while missing task repo' '
	gistore task add hello repo1.git &&
	gistore task add world repo2.git &&
	gistore task list | grep -q "$cwd" &&
	gistore task list | sed -e "/^$/d" | \
		sed -e "s#${cwd}/##g" | sort -u > actual &&
	test_cmp expect actual &&
	do_hack &&
	gistore commit-all &&
	test "$(count_git_commits repo1.git)" = "5" &&
	test "$(count_git_commits repo2.git)" = "4" &&
	mv repo1.git repo1.git.moved &&
	do_hack &&
	test_must_fail gistore commit-all &&
	test "$(count_git_commits repo2.git)" = "5" &&
	mv repo1.git.moved repo1.git &&
	mv repo2.git repo2.git.moved &&
	test_must_fail gistore commit-all
	test "$(count_git_commits repo1.git)" = "6"
'

test_done

#!/bin/sh
#
# Copyright (c) 2013 Jiang Xin
#

test_description='Test gistore commit'

TEST_NO_CREATE_REPO=NoPlease
. ./lib-worktree.sh
. ./test-lib.sh

cwd=$(pwd -P)

cat >expect << EOF
root/doc/COPYRIGHT
root/src/README.txt
root/src/images/test-binary-1.png
root/src/images/test-binary-2.png
root/src/lib/a/foo.c
root/src/lib/b/bar.o
root/src/lib/b/baz.a
EOF

# test_expect_success 'remove to avoid .gitignore side-effect' '
# 	if [ -f "$TEST_DIRECTORY/.gitignore" ]; then
# 		mv  "$TEST_DIRECTORY/.gitignore" "$TEST_DIRECTORY/.gitignore.save"
# 	fi
# '

test_expect_success 'initialize for commit' '
	prepare_work_tree &&
	gistore init --repo repo.git &&
	gistore add --repo repo.git root/src &&
	gistore add --repo repo.git root/doc &&
	gistore commit --repo repo.git &&
	test "$(count_git_commits repo.git)" = "1" &&
	gistore repo repo.git ls-tree --name-only \
		-r HEAD | sed -e "s#^${cwd#/}/##g" > actual &&
	test_cmp expect actual
'

test_expect_success 'nothing changed, no commit' '
	gistore commit --repo repo.git &&
	touch root/src/README.txt &&
	gistore commit --repo repo.git &&
	test "$(count_git_commits repo.git)" = "1"
'

test_expect_success 'commit if something changed' '
	echo "more" >> root/src/README.txt &&
	gistore commit --repo repo.git &&
	test "$(count_git_commits repo.git)" = "2"
'

cat >expect << EOF
root/doc/COPYRIGHT
root/src/README.txt
root/src/images/test-binary-1.png
root/src/images/test-binary-2.png
root/src/lib/a/foo.c
root/src/lib/b/bar.o
EOF

test_expect_success 'commit if something removed' '
	rm root/src/lib/b/baz.a &&
	gistore commit --repo repo.git &&
	test "$(count_git_commits repo.git)" = "3"
	gistore repo repo.git ls-tree --name-only \
		-r HEAD | sed -e "s#^${cwd#/}/##g" > actual &&
	test_cmp expect actual
'

cat >expect << EOF
root/doc/COPYRIGHT
root/new_src/README.txt
root/new_src/images/test-binary-1.png
root/new_src/images/test-binary-2.png
root/new_src/lib/a/foo.c
root/new_src/lib/b/bar.o
root/src
EOF

test_expect_success 'commit even for symlink' '
	mv root/src root/new_src &&
	ln -s new_src root/src &&
	gistore commit --repo repo.git &&
	test "$(count_git_commits repo.git)" = "4"
	gistore repo repo.git ls-tree --name-only \
		-r HEAD | sed -e "s#^${cwd#/}/##g" > actual &&
	test_cmp expect actual
'

cat >expect << EOF
root/doc/COPYRIGHT
EOF

test_expect_success 'not backup root/src any more' '
	gistore rm --repo repo.git root/src &&
	gistore commit --repo repo.git &&
	test -L root/src &&
	test -f root/new_src/README.txt &&
	test -f root/new_src/images/test-binary-1.png &&
	test -f root/new_src/lib/a/foo.c &&
	test -f root/new_src/lib/b/bar.o &&
	gistore repo repo.git ls-tree --name-only \
		-r HEAD | sed -e "s#^${cwd#/}/##g" > actual &&
	test_cmp expect actual
'

cat >expect << EOF
root/doc/COPYRIGHT
root/mod1/README.txt
root/mod1/lib/doc/bar.txt
root/mod1/lib/src/foo.c
root/mod2/README.txt
root/mod2/doc/bar.txt
root/mod2/lib/hello.txt
root/mod2/src/foo.c
EOF

test_expect_success 'add real files instead of submodule' '
	gistore add --repo repo.git root/mod1 &&
	gistore add --repo repo.git root/mod2 &&
	gistore commit --repo repo.git &&
	gistore repo repo.git ls-tree --name-only \
		-r HEAD | sed -e "s#^${cwd#/}/##g" > actual &&
	test_cmp expect actual
'

# test_expect_success 'restore .gitignore' '
# 	if [ -f "$TEST_DIRECTORY/.gitignore.save" ]; then
# 		mv  "$TEST_DIRECTORY/.gitignore.save" "$TEST_DIRECTORY/.gitignore"
# 	fi
# '


test_done

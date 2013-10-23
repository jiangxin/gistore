#!/bin/sh
#
# Copyright (c) 2013 Jiang Xin
#

test_description='Test gistore checkout'

TEST_NO_CREATE_REPO=NoPlease
. ./lib-worktree.sh
. ./test-lib.sh

do_hack()
{
	echo "hack $*" >> root/src/README.txt
	echo "hack $*" >> root/doc/COPYRIGHT
}

cwd=$(pwd -P)

cat >expect << EOF
outdir/.git
outdir/root/doc/COPYRIGHT
EOF

test_expect_success 'initialize for checkout' '
	prepare_work_tree &&
	gistore init --repo repo.git &&
	gistore init --repo repo2.git &&
	gistore add  --repo repo.git root/doc &&
	gistore add  --repo repo2.git root/doc &&
	gistore commit --repo repo.git -m "initialize for checkout" &&
	gistore commit --repo repo2.git -m "initialize for checkout" &&
	gistore checkout  --repo repo.git --to outdir &&
	find outdir -type f | sed -e "s#${cwd}##g" | sort > actual &&
	test_cmp expect actual
'

cat >expect << EOF
outdir/.git
outdir/root/doc/COPYRIGHT
outdir/root/src/README.txt
outdir/root/src/images/test-binary-1.png
outdir/root/src/images/test-binary-2.png
outdir/root/src/lib/a/foo.c
outdir/root/src/lib/b/bar.o
outdir/root/src/lib/b/baz.a
EOF

test_expect_success 'checkout continue' '
	gistore add  --repo repo.git root/src &&
	gistore commit --repo repo.git -m "checkout continue" &&
	gistore checkout --repo repo.git --to outdir &&
	find outdir -type f | sed -e "s#${cwd}##g" | sort > actual &&
	test_cmp expect actual
'

cat >expect << EOF
partial/.git
partial/root/src/lib/a/foo.c
partial/root/src/lib/b/bar.o
partial/root/src/lib/b/baz.a
EOF

test_expect_success 'partial checkout' '
	gistore checkout --repo repo.git --to partial "${cwd#/}/root/src/lib" &&
	find partial -type f | sed -e "s#${cwd}##g" | sort > actual &&
	test_cmp expect actual
'

cat >expect << EOF
history/.git
history/root/doc/COPYRIGHT
EOF

test_expect_success 'checkout history' '
	gistore checkout --repo repo.git --to history --rev HEAD^ &&
	find history -type f | sed -e "s#${cwd}##g" | sort > actual &&
	test_cmp expect actual
'

test_expect_success 'worktree and gitdir unmatch' '
	test_must_fail gistore checkout  --repo repo2.git --to outdir
'

test_expect_success 'not checkout to no empty dir' '
	mkdir outdir2 && touch outdir2/.hidden &&
	test_must_fail gistore checkout  --repo repo2.git --to outdir2 &&
	rm outdir2/.hidden &&
	gistore checkout  --repo repo2.git --to outdir2
'

test_done

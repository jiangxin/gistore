#!/bin/sh
#
# Copyright (c) 2013 Jiang Xin
#

test_description='Test gistore init'

TEST_NO_CREATE_REPO=NoThanks
. ./test-lib.sh

test_expect_success 'init with default normal plan' '
	(
		mkdir default &&
		cd default &&
		gistore init &&
		test "$(gistore config plan)" = "normal"
	)
'

cat >expect <<EOF
Repository format 1
EOF

test_expect_success 'check repo format version' '
	gistore --version --repo default | tail -1 > actual &&
	test_cmp expect actual
'

cat >expect <<EOF
Error: Non-empty directory 'default' is already exist.
EOF

test_expect_success 'can not init on a no-empty directory' '
	test_must_fail gistore init --repo default &&
	(gistore init --repo default 2>actual || true ) &&
	test_cmp expect actual
'

test_expect_success 'check default gistore/git configurations' '
	(
		cd default &&
		test "$(gistore config full_backup_number)" = "12" &&
		test "$(gistore config increment_backup_number)" = "30" &&
		test -z "$(gistore config gc.auto)" &&
		test -z "$(gistore config core.compression)" &&
		test -z "$(gistore config core.loosecompression)" &&
		test "$(gistore config --bool core.quotepath)" = "false" &&
		test "$(gistore config --bool core.autocrlf)" = "false" &&
		test "$(gistore config --bool core.logAllRefUpdates)" = "true" &&
		test "$(gistore config core.sharedRepository)" = "group" &&
		test "$(gistore config core.bigFileThreshold)" = "2m"
	)
'

test_expect_success 'init with --no-compress plan' '
	(
		gistore init --repo notz --plan no-compress &&
		test "$(gistore config --repo notz plan)" = "no-compress" &&
		test -z "$(gistore config --repo notz gc.auto)" &&
		test "$(gistore config --repo notz core.compression)" = "0" &&
		test "$(gistore config --repo notz core.loosecompression)" = "0"
	)
'

test_expect_success 'init with --no-gc plan' '
	(
		gistore init --repo notgc --plan no-gc &&
		test "$(gistore config --repo notgc plan)" = "no-gc" &&
		test "$(gistore config --repo notgc gc.auto)" = "0" &&
		test "$(gistore config --repo notgc core.compression)" = "0" &&
		test "$(gistore config --repo notgc core.loosecompression)" = "0"
	)
'

test_done

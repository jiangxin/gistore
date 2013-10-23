#!/bin/sh
#
# Copyright (c) 2013 Jiang Xin
#

test_description='Test gistore config'

TEST_NO_CREATE_REPO=
. ./test-lib.sh

test_expect_success 'default is normal plan' '
	test "$(gistore config plan)" = "normal"
'

test_expect_success 'check default gistore configurations' '
	test "$(gistore config full_backup_number)" = "12" &&
	test "$(gistore config increment_backup_number)" = "30"
	test -z "$(gistore config gc.auto)" &&
	test -z "$(gistore config core.compression)" &&
	test -z "$(gistore config core.loosecompression)" &&
	test "$(gistore config --bool core.quotepath)" = "false" &&
	test "$(gistore config --bool core.autocrlf)" = "false" &&
	test "$(gistore config --bool core.logAllRefUpdates)" = "true" &&
	test "$(gistore config core.sharedRepository)" = "group" &&
	test "$(gistore config core.bigFileThreshold)" = "2m"
'

test_expect_success 'change plan from normal to no-gc' '
	test "$(gistore config plan)" = "normal" &&
	gistore config --plan no-gc &&
	test "$(gistore config plan)" = "no-gc" &&
	test "$(gistore config gc.auto)" = "0" &&
	test "$(gistore config core.compression)" = "0" &&
	test "$(gistore config core.loosecompression)" = "0"
'

test_expect_success 'change plan from no-gc to no-compress' '
	test "$(gistore config plan)" = "no-gc" &&
	gistore config --plan no-compress &&
	test "$(gistore config plan)" = "no-compress" &&
	test -z "$(gistore config gc.auto)" &&
	test "$(gistore config core.compression)" = "0" &&
	test "$(gistore config core.loosecompression)" = "0"
'

test_expect_success 'change plan without --plan option' '
	test "$(gistore config plan)" = "no-compress" &&
	gistore config plan no-gc &&
	gistore config plan normal &&
	test "$(gistore config plan)" = "normal" &&
	test -z "$(gistore config gc.auto)" &&
	test -z "$(gistore config core.compression)" &&
	test -z "$(gistore config core.loosecompression)"
'

test_expect_success 'read/write gistore configurations' '
	test "$(gistore config full_backup_number)" = "12" &&
	test "$(gistore config increment_backup_number)" = "30" &&
	gistore config full_backup_number 5 &&
	gistore config increment_backup_number 9 &&
	test "$(gistore config full_backup_number)" = "5" &&
	test "$(gistore config increment_backup_number)" = "9" &&
	test_must_fail gistore config non_exist_config value &&
	test_must_fail gistore config --unset non.exist.config
'

test_expect_success 'read/write git configurations' '
	gistore config x.y.z foobar &&
	test "$(gistore config x.y.z)" = "foobar" &&
	test "$(git config x.y.z)" = "foobar" &&
	git config x.y.z baz &&
	test "$(gistore config x.y.z)" = "baz"
'

test_done

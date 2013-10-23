#!/bin/sh
#
# Copyright (c) 2013 Jiang Xin
#

test_description='Test git version compare'

TEST_NO_CREATE_REPO=NoThanks
. ./test-lib.sh

test_expect_success 'compare two versions' '
	test $(gistore check-git-version 1.8.5 1.8.5) -eq 0 &&
	test $(gistore check-git-version 1.8.4 1.8.4.1) -eq -1 &&
	test $(gistore check-git-version 1.7.5 1.7.11) -eq -1 &&
	test $(gistore check-git-version 1.7.11 1.7.5) -eq 1 &&
	test $(gistore check-git-version 1.7.11 1.7.5) -eq 1 &&
	test $(gistore check-git-version 1.7.11 2.0) -eq -1 &&
	test $(gistore check-git-version 2.0 1.8.5) -eq 1
'

test_expect_success 'compare with current version' '
	test $(gistore check-git-version 0.99.1) -eq 1 &&
	test $(gistore check-git-version 0.99.1.2) -eq 1
'

test_done

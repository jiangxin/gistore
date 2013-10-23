#!/bin/sh
#
# Copyright (c) 2013 Jiang Xin
#

test_description='Test gistore export and restore'

TEST_NO_CREATE_REPO=NoPlease
. ./lib-worktree.sh
. ./test-lib.sh

do_hack()
{
	echo "hack $*" >> root/src/README.txt
	echo "hack $*" >> root/doc/COPYRIGHT
}

cwd=$(pwd -P)
n=0

cat >expect << EOF
Backup No. 24
Backup No. 23
Backup No. 22
Full backup of repo.git
Backup No. 20
Backup No. 19
Backup No. 18
Backup No. 17
Full backup of repo.git
Backup No. 15
Backup No. 14
Backup No. 13
Backup No. 12
Full backup of repo.git
Backup No. 10
Backup No. 9
Backup No. 8
Backup No. 7
Full backup of repo.git
EOF

test_expect_success 'initialize for export' '
	prepare_work_tree &&
	gistore init --repo repo.git &&
	gistore config --repo repo.git full_backup_number 3 &&
	gistore config --repo repo.git increment_backup_number 5 &&
	gistore add --repo repo.git root/src &&
	gistore add --repo repo.git root/doc &&
	i=0 &&
	while test $i -lt 24; do
		i=$((i+1));
		n=$((n+1));
		do_hack $n;
		gistore commit --repo repo.git -m "Backup No. $n";
	done &&
	test "$(count_git_commits repo.git)" = "19" &&
	git_log_only_subject repo.git > actual &&
	test_cmp expect actual &&
	test "$(count_git_objects repo.git)" = "349" &&
	gistore gc --repo repo.git --force &&
	test "$(count_git_objects repo.git)" = "278"
'

test_expect_success 'export backups' '
	gistore export-to-backups --repo repo.git --to backups &&
	test $(ls backups/001-full-backup-*.pack | wc -l) -eq 1 &&
	test $(ls backups/*-incremental-*.pack | wc -l) -eq 3
'

cat >expect <<EOF
Backup No. 24
Backup No. 23
Backup No. 22
Full backup of repo.git
EOF

test_expect_success 'restore from backups' '
	gistore restore-from-backups --from backups --to restore.git &&
	test $(count_git_objects restore.git) -eq 65 &&
	test $(count_git_commits restore.git) -eq 4 &&
	git_log_only_subject restore.git > actual &&
	test_cmp expect actual
'

test_expect_success 'export another repo' '
	gistore init --repo repo2.git &&
	gistore config --repo repo2.git full_backup_number 3 &&
	gistore config --repo repo2.git increment_backup_number 5 &&
	gistore add --repo repo2.git root/src &&
	i=0 && n=0 &&
	while test $i -lt 2; do
		i=$((i+1));
		n=$((n+1));
		do_hack $n;
		gistore commit --repo repo2.git -m "Repo2 commit No. $n";
	done &&
	test $(count_git_commits repo2.git) -eq 2 &&
	test $(count_git_objects repo2.git) -eq 33 &&
	gistore export-to-backups --repo repo2.git --to backups2 &&
	test $(ls backups2/001-full-backup-*.pack | wc -l) -eq 1 &&
	test $(ls backups2/*-incremental-*.pack | wc -l) -eq 1
'

cat >expect <<EOF
Repo2 commit No. 2
Repo2 commit No. 1
EOF

test_expect_success 'restore from backups2' '
	gistore restore-from-backups --from backups2 --to restore.git >result 2>&1 &&
	new_commit=$(grep $_x40 result) &&
	test $(count_git_commits restore.git) -eq 4 &&
	test $(count_git_objects restore.git) -eq 89 &&
	(
		cd restore.git;
		git update-ref refs/heads/master $new_commit;
	) &&
	git_log_only_subject restore.git > actual &&
	test_cmp expect actual
'

test_done

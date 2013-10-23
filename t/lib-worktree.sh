#!/bin/sh
#
# Copyright (c) 2013 Jiang Xin
#

prepare_work_tree()
{
	mkdir -p root/src/lib/a
	mkdir -p root/src/lib/b
	mkdir -p root/src/lib/empty
	mkdir -p root/src/images
	mkdir -p root/doc/
	echo "readme"		> root/src/README.txt
	echo "foo"			> root/src/lib/a/foo.c
	echo "bar"			> root/src/lib/b/bar.o
	echo "baz"			> root/src/lib/b/baz.a
	cp ${TEST_DIRECTORY}/test-binary-1.png root/src/images
	cp ${TEST_DIRECTORY}/test-binary-2.png root/src/images
	echo "copyright"		> root/doc/COPYRIGHT
	touch root/.hidden

	mkdir -p root/mod1/
	(
		cd root/mod1
		echo "readme" > README.txt
		mkdir lib
		cd lib
		git init
		mkdir src doc
		echo "foo" > src/foo.c
		echo "bar" > doc/bar.txt
		git add -A .
		git commit -m 'initial submodule mod1'
	)
	mkdir -p root/mod2/
   	(
		cd root/mod2
		git init
		echo "readme" > README.txt
		mkdir src doc
		echo "foo" > src/foo.c
		echo "bar" > doc/bar.txt
		git add -A .
		git commit -m 'initial submodule mod2'
		mkdir lib
		cd lib
		git init
		echo "hello" > hello.txt
		git add -A .
		git commit -m 'initial lib under mod2'
	)
}

count_git_commits()
{
	repo=$1
	git --git-dir "$repo" rev-list HEAD 2>/dev/null | wc -l | sed -e 's/ //g'
}

count_git_objects()
{
	repo=$1
	num=0
	git --git-dir "$repo" count-objects -v | sort | \
	while read line; do
		case $line in
		count:*)
			num=$((num + ${line#count:}))
			;;
		in-pack:*)
			num=$((num + ${line#in-pack:}))
			echo $num
			;;
		esac
	done
}

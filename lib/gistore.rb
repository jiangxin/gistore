#!/usr/bin/env ruby
# encoding: UTF-8

std_trap = trap("INT") { exit! 130 } # no backtrace thanks

require 'pathname'
LIBRARY_PATH = Pathname.new(__FILE__).realpath.dirname.to_s
$:.unshift(LIBRARY_PATH + '/gistore/vendor')
$:.unshift(LIBRARY_PATH)

require 'gistore/runner'
require 'gistore/utils'

abort "Please install git first" unless git_cmd
if Gistore.git_version_compare('1.6.0') < 0
  abort "Git lower than 1.6.0 has not been tested. Please upgrade your git."
end

$gistore_runner = true
Gistore::Runner.start

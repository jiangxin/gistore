require 'gistore/repo'
require 'gistore/utils'
require 'gistore/version'

module Gistore
  class Runner
    desc "init", "Initialize gistore repository"
    long_desc <<-LONGDESC
      `gistore init <repo>` will create a gistore backup repo.

      The created <repo> is a bare git repository, and when excute backup and/or
      other commands on <repo>, GIT_WORK_TREE will be set as '/', and GIT_DIR
      will be set as <repo> automatically.

      This bare repo has been set with default settings which are suitable for
      backup for text files. But if most of the backups are binaries, you may
      like to set <repo> with custom settings. You can give specific plan for
      <repo> when initializing, like:

      > $ gistore init --plan <no-gc|no-compress|normal> <repo>

      Or run `gistore config` command latter, like

      > $ gistore config --repo <repo> --plan no-compress
      \x5> $ gistore config --repo <repo> --plan no-gc
    LONGDESC
    option :plan, :required => false, :type => :string,
           :desc => "no-gc, no-compress, or normal (default)"
    def init(name=nil)
      Repo.init(options[:repo] || name || ".", options)
    rescue Exception => e
      $stderr.puts "Error: #{e.message}"
    end
  end
end

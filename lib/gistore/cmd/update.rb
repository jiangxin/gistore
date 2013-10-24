require 'pathname'

module Gistore
  class Runner
    map "up" => :update
    desc "update", "Update gistore from github.com"
    option :url, :type => :string, :desc => "Repository URL"
    option :rebase, :type => :boolean, :desc => "Rebase instead of merge"
    def update
      parse_common_options
      report = Gistore::Report.new
      gistore_updater = Gistore::Updater.new(options)
      Dir.chdir(GISTORE_REPOSITORY) do
        # initial git repo if necessary
        unless Gistore.is_git_repo? ".git"
          gistore_updater.git_init
        end

        # git pull
        gistore_updater.pull!
        report.merge!(gistore_updater.report)
        if report.empty?
          Tty.info "Already up-to-date."
        else
          Tty.info "Updated Gistore from #{gistore_updater.initial_revision[0,8]} to #{gistore_updater.current_revision[0,8]}."
          report.dump
        end
      end
    rescue Exception => e
      Tty.die "#{e.message}"
    end
  end

  class Updater
    attr_reader :initial_revision, :current_revision

    def initialize(options={})
      @url = options[:url] || Gistore::GISTORE_REPOSITORY_URL
      @options = options
    end

    def git_init
      Gistore.safe_system git_cmd, "init"
      Gistore.safe_system git_cmd, "config", "core.autocrlf", "false"
      Gistore.safe_system git_cmd, "remote", "add", "origin", @url
      Gistore.safe_system git_cmd, "fetch", "origin"
      Gistore.safe_system git_cmd, "reset", "origin/master"
      # Gistore.safe_system git_cmd, "stash", "save"
    end

    def pull!
      Gistore.safe_system git_cmd, "checkout", "-q", "master"

      @initial_revision = read_current_revision

      # ensure we don't munge line endings on checkout
      Gistore.safe_system git_cmd, "config", "core.autocrlf", "false"

      args = [git_cmd, "pull"]
      args << "--rebase" if @options[:rebase]
      args << "-q" unless @options[:verbose]
      args << "origin"
      # the refspec ensures that 'origin/master' gets updated
      args << "refs/heads/master:refs/remotes/origin/master"

      reset_on_interrupt { Gistore.safe_system *args }

      @current_revision = read_current_revision
    end

    def reset_on_interrupt
      ignore_interrupts { yield }
    ensure
      if $?.signaled? && $?.termsig == 2 # SIGINT
        Gistore.safe_system git_cmd, "reset", "--hard", @initial_revision
      end
    end

    def ignore_interrupts(opt = nil)
      std_trap = trap("INT") do
        puts "One sec, just cleaning up" unless opt == :quietly
      end
      yield
    ensure
      trap("INT", std_trap)
    end

    # Matches raw git diff format (see `man git-diff-tree`)
    DIFFTREE_RX = /^:[0-7]{6} [0-7]{6} [0-9a-fA-F]{40} [0-9a-fA-F]{40} ([ACDMR])\d{0,3}\t(.+?)(?:\t(.+))?$/

    def report
      map = Hash.new{ |h,k| h[k] = [] }

      if initial_revision && initial_revision != current_revision
        `#{git_cmd} diff-tree -r --raw -M85% #{initial_revision} #{current_revision}`.each_line do |line|
          DIFFTREE_RX.match line
          path = case status = $1.to_sym
            when :R then $3
            else $2
            end
          path = Pathname.pwd.join(path).relative_path_from(Pathname.new(GISTORE_REPOSITORY))
          map[status] << path.to_s
        end
      end

      map
    end

    private

    def read_current_revision
      `#{git_cmd} rev-parse -q --verify HEAD`.chomp
    end

    def `(cmd)
      out = Kernel.`(cmd) #`
      if $? && !$?.success?
        $stderr.puts out
        raise CommandReturnError, "Failure while executing: #{cmd}"
      end
      Tty.debug "Command: #{cmd}.\nOutput: #{out}"
      out
    end
  end

  class Report < Hash

    def dump
      # Key Legend: Added (A), Copied (C), Deleted (D), Modified (M), Renamed (R)
      dump_report :A, "New"
      dump_report :C, "Copy"
      dump_report :M, "Modified"
      dump_report :D, "Deleted"
      dump_report :R, "Renamed"
    end

    def dump_report(key, title)
      entries = fetch(key, [])
      unless entries.empty?
        puts "#{Tty.blue}==>#{Tty.white} #{title}#{Tty.reset}"
        puts Tty.show_columns entries.uniq
      end
    end
  end

end

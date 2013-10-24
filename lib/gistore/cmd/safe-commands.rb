module Gistore
  SAFE_GIT_COMMANDS = %w(
        annotate        blame           branch          cat-file        check-ignore
        count-objects   describe        diff            fsck            grep
        log             lost-found      ls-files        ls-tree         name-rev
        prune           reflog          rev-list        rev-parse       shortlog
        show            show-ref        status          tag             whatchanged)

  class Runner
    desc "repo <repo> git-command ...", "Delegate to safe git commands (log, ls-tree, ...)"
    option :without_grafts, :type => :boolean, :desc => "not check info/grafts"
    option :without_work_tree, :type => :boolean, :desc => "not change work tree"
    option :without_locale, :type => :boolean, :desc => "use locale C"
    def repo (name, cmd=nil, *args, &block)
      parse_common_options
      if options[:repo]
        args ||= []
        args.unshift cmd if cmd
        name, cmd = options[:repo], name
      end
      cmd = args.shift if cmd == "git"
      if Gistore::SAFE_GIT_COMMANDS.include? cmd
        opts = options.dup
        opts.delete("repo")
        args << opts
        gistore = Repo.new(name || ".")
        gistore.safe_system(git_cmd, cmd, *args)
      elsif self.respond_to? cmd
        # Because command may have specific options mixed in args,
        # can not move options from args easily. So we not call
        # invoke here, but call Gistore::Runner.start.
        Gistore::Runner.start([cmd, "--repo", name, *args])
      else
        raise "Command \"#{cmd}\" is not allowed.\n"
      end
    rescue Exception => e
      Tty.die "#{e.message}"
    end

    desc "log args...", "Show gistore backup logs (delegater for git log)"
    option :without_grafts, :type => :boolean, :desc => "not check info/grafts"
    option :without_work_tree, :type => :boolean, :desc => "not change work tree"
    option :without_locale, :type => :boolean, :desc => "use locale C"
    def log(*args)
      if options[:repo]
        repo('log', *args)
      else
        name = args.shift || "."
        repo(name, 'log', *args)
      end
    end
  end
end

module Gistore
  class Task < Thor; end

  class Runner
    desc "task SUBCOMMAND ...ARGS", "manage set of tracked repositories"
    subcommand "task", Gistore::Task
  end

  class Task < Thor
    # Use command name "gistore" in help instead of "gistore.rb"
    def self.basename; "gistore"; end

    # Show in help screen
    package_name "Gistore"

    desc "add <task> [<repo>]", "Register repo as a task"
    option :system, :type => :boolean
    def add(task, path=nil)
      parse_common_options
      path ||= "."
      cmds = [git_cmd, "config"]
      unless ENV["GISTORE_TEST_GIT_CONFIG"]
        ENV.delete "GIT_CONFIG"
        if options[:system]
          cmds << "--system"
        else
          cmds << "--global"
        end
      end
      cmds << "gistore.task.#{task}"
      cmds << File.expand_path(path)
      system(*cmds)
    rescue Exception => e
      Tty.die "#{e.message}"
    end

    desc "rm <task>", "Remove register of task"
    option :system, :type => :boolean
    def rm(task)
      parse_common_options
      cmds = [git_cmd, "config", "--unset"]
      unless ENV["GISTORE_TEST_GIT_CONFIG"]
        ENV.delete "GIT_CONFIG"
        if options[:system]
          cmds << "--system"
        else
          cmds << "--global"
        end
      end
      cmds << "gistore.task.#{task}"
      Kernel::system(*cmds)
    rescue Exception => e
      Tty.die "#{e.message}"
    end
    
    desc "list", "Display task list"
    option :system, :type => :boolean
    option :global, :type => :boolean
    def list(name=nil)
      parse_common_options
      if name
        invoke "gistore:runner:status", [], :repo => name
      else
        puts "System level Tasks"
        tasks = Gistore::get_gistore_tasks(:system => true)
        puts Tty.show_columns tasks.to_a.map {|h| "#{h[0]} => #{h[1]}"}
        puts
        puts "User level Tasks"
        tasks = Gistore::get_gistore_tasks(:global => true)
        puts Tty.show_columns tasks.to_a.map {|h| "#{h[0]} => #{h[1]}"}
      end
    end

    private

    def parse_common_options
      if options[:verbose]
        Tty.options[:verbose] = true
      elsif options[:quiet]
        Tty.options[:quiet] = true
      end
    end

  end
end

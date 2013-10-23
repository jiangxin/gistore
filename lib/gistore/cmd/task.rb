module GistoreCli
  class SubCommandTask < Thor
    desc "add <task> [<repo>]", "Register repo as a task"
    option :system, :type => :boolean
    def add(task, path=nil)
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
      Kernel::system(*cmds)
    rescue Exception => e
      $stderr.puts "Error: #{e.message}"
    end

    desc "rm <task>", "Remove register of task"
    option :system, :type => :boolean
    def rm(task)
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
      $stderr.puts "Error: #{e.message}"
    end
    
    desc "list", "Display task list"
    option :system, :type => :boolean
    option :global, :type => :boolean
    def list(name=nil)
      if name
        invoke "gistore:runner:status", [], :repo => name
      else
        puts "System level Tasks"
        tasks = Gistore::get_gistore_tasks(:system => true)
        puts Gistore.show_column tasks.to_a.map {|h| "#{h[0]} => #{h[1]}"}
        puts
        puts "User level Tasks"
        tasks = Gistore::get_gistore_tasks(:global => true)
        puts Gistore.show_column tasks.to_a.map {|h| "#{h[0]} => #{h[1]}"}
      end
    end
  end
end

module Gistore
  class Runner
    desc "task SUBCOMMAND ...ARGS", "manage set of tracked repositories"
    subcommand "task", GistoreCli::SubCommandTask
  end
end

module Gistore
  class Runner
    desc "export-to-backups", "Export to a series of full/increment backups"
    option :to, :required => true, :banner => "<dir>", :desc => "path to save full/increment backups"
    def export_to_backups
      parse_common_options_and_repo
      work_tree = options[:to]
      if File.exist? work_tree
        if not File.directory? work_tree
          raise "\"#{work_tree}\" is not a valid directory."
        elsif Dir.entries(work_tree).size != 2
          Tty.warning "\"#{work_tree}\" is not a blank directory."
        end
      else
        require 'fileutils'
        FileUtils.mkdir_p work_tree
      end

      commits = []
      gistore.shellout(git_cmd, "rev-list", "master",
                       :without_grafts => true) do |stdout|
        commits = stdout.readlines
      end

      export_commits(commits, work_tree)
    rescue Exception => e
      Tty.die "#{e.message}"
    end

  private

    def export_commits(commits, work_tree)
      left = right = nil
      n = 1
      until commits.empty?
        right=commits.pop.strip
        export_one_commit(n, left, right, work_tree)
        left = right
        n += 1
      end
    end

    def export_one_commit(n, left, right, work_tree)
      time = nil
      gistore.shellout(git_cmd, "cat-file", "commit", right) do |stdout|
        stdout.readlines.each do |line|
          if line =~ /^committer .* ([0-9]+)( [+-][0-9]*)?$/
            time = Time.at($1.to_i).strftime("%Y%m%d-%H%M%S")
            break
          end
        end
      end

      prefix = "%03d-" % n
      prefix << (left ? "incremental" : "full-backup")
      prefix << "-#{time}" if time
      prefix << "-g#{right[0...7]}"

      if not Dir.glob("#{work_tree}/#{prefix}*.pack").empty?
        Tty.info "already export commit #{right}"
        return
      end

      if left
        input_rev = "#{left}..#{right}"
      else
        input_rev = right
      end

      gistore.shellpipe(git_cmd, "pack-objects", "--revs", prefix,
                        :without_grafts => true,
                        :work_tree => work_tree) do |stdin, stdout, stderr|
        stdin.write input_rev
        stdin.close_write
      end
      Tty.info "export #{n}: #{prefix}"
    end
  end
end

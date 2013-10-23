module Gistore
  class Runner
    desc "rm <path> ...", "Remove entry from backup list"
    def rm(*args)
      gistore = Repo.new(options[:repo] || ".")
      args.each do |entry|
        gistore.remove_entry entry
      end
      gistore.save_gistore_backups
    rescue Exception => e
      $stderr.puts "Error: #{e.message}"
    end
  end
end

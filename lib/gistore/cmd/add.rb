module Gistore
  class Runner
    desc "add <path> ...", "Add path to backup list"
    def add(*args)
      parse_common_options
      args.each do |entry|
        gistore.add_entry entry
      end
      gistore.save_gistore_backups
    rescue Exception => e
      $stderr.puts "Error: #{e.message}"
    end
  end
end

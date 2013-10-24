module Gistore

  DEFAULT_GISTORE_CONFIG = {"backups" => [],
                            "plan" => nil,
                            "increment_backup_number" => 30,
                            "full_backup_number" => 12,
                            "user_name" => nil,
                            "user_email" => nil
                           }
  GISTORE_REPOSITORY_URL = "git://github.com/jiangxin/gistore"
  GISTORE_REPOSITORY = File.dirname(File.dirname(File.dirname(__FILE__)))

end

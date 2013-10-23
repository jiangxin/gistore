require 'gistore/utils'

module Gistore
  class Runner
    desc "check-git-version", "Check git version", :hide => true
    def check_git_version(v1, v2=nil)
      if v2
        puts Gistore.git_version_compare(v1, v2)
      else
        puts Gistore.git_version_compare(v1)
      end
    end
  end
end

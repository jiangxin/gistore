module Gistore
  class CommandReturnError < StandardError; end
  class CommandExceptionError < StandardError; end
  class InvalidRepoError < StandardError; end
  class CommandExit < StandardError; end
end

class Spyglass < Formula
  include Language::Python::Virtualenv

  desc "Keep selected Apple Containers up to date"
  homepage "https://github.com/wolfpaulus/spyglass"
  url "https://files.pythonhosted.org/packages/00/87/b60911e53090b8e0190d6f11c93ffd54bd6eee5d0fd71262ee0a21b46e17/apple_container_spyglass-1.0.1.tar.gz"
  sha256 "af303f4cb798cc19c32ae03569cf4f3b301e648f2be995e8adb4b8558930a494"
  license "MIT"

  depends_on "python@3.15"

  def install
    virtualenv_install_with_resources
  end

  service do
    run [opt_bin/"spyglass"]
    run_at_load true
    run_type :interval
    interval 3600
    environment_variables PATH: std_service_path_env
  end

  test do
    fake_container = testpath/"container"
    fake_container.write <<~EOS
      #!/bin/sh
      echo '[]'
    EOS
    fake_container.chmod 0755

    ENV["HOME"] = testpath.to_s
    ENV.prepend_path "PATH", testpath
    system bin/"spyglass"
  end
end

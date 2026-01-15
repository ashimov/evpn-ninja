# Homebrew formula for vxlan-calculator
# To install from local tap:
#   brew tap ashimov/vxlan-calculator https://github.com/ashimov/vxlan-calculator
#   brew install vxlan-calculator
#
# Or install directly:
#   brew install --HEAD ashimov/vxlan-calculator/vxlan-calculator

class VxlanCalculator < Formula
  include Language::Python::Virtualenv

  desc "VXLAN/EVPN Calculator CLI - VNI allocation, fabric planning, MTU calculation"
  homepage "https://github.com/ashimov/vxlan-calculator"
  url "https://files.pythonhosted.org/packages/source/v/vxlan-calculator/vxlan_calculator-1.0.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"
  head "https://github.com/ashimov/vxlan-calculator.git", branch: "main"

  depends_on "python@3.12"

  resource "typer" do
    url "https://files.pythonhosted.org/packages/source/t/typer/typer-0.12.5.tar.gz"
    sha256 "PLACEHOLDER_SHA256_TYPER"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.9.4.tar.gz"
    sha256 "PLACEHOLDER_SHA256_RICH"
  end

  resource "questionary" do
    url "https://files.pythonhosted.org/packages/source/q/questionary/questionary-2.0.1.tar.gz"
    sha256 "PLACEHOLDER_SHA256_QUESTIONARY"
  end

  resource "PyYAML" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/pyyaml-6.0.2.tar.gz"
    sha256 "PLACEHOLDER_SHA256_PYYAML"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.1.7.tar.gz"
    sha256 "PLACEHOLDER_SHA256_CLICK"
  end

  resource "markdown-it-py" do
    url "https://files.pythonhosted.org/packages/source/m/markdown-it-py/markdown_it_py-3.0.0.tar.gz"
    sha256 "PLACEHOLDER_SHA256_MARKDOWN_IT_PY"
  end

  resource "pygments" do
    url "https://files.pythonhosted.org/packages/source/P/Pygments/pygments-2.18.0.tar.gz"
    sha256 "PLACEHOLDER_SHA256_PYGMENTS"
  end

  resource "mdurl" do
    url "https://files.pythonhosted.org/packages/source/m/mdurl/mdurl-0.1.2.tar.gz"
    sha256 "PLACEHOLDER_SHA256_MDURL"
  end

  resource "prompt-toolkit" do
    url "https://files.pythonhosted.org/packages/source/p/prompt_toolkit/prompt_toolkit-3.0.48.tar.gz"
    sha256 "PLACEHOLDER_SHA256_PROMPT_TOOLKIT"
  end

  resource "wcwidth" do
    url "https://files.pythonhosted.org/packages/source/w/wcwidth/wcwidth-0.2.13.tar.gz"
    sha256 "PLACEHOLDER_SHA256_WCWIDTH"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    # Test basic CLI functionality
    assert_match "VXLAN", shell_output("#{bin}/vxlan --help")

    # Test MTU calculation
    output = shell_output("#{bin}/vxlan mtu --payload 1500 --output json")
    assert_match "required_mtu", output

    # Test VNI allocation
    output = shell_output("#{bin}/vxlan vni --count 5 --output json")
    assert_match "entries", output

    # Test version
    assert_match version.to_s, shell_output("#{bin}/vxlan -V")
  end
end

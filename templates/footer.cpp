template <typename T>
void expectEqual(const std::string& testName, const T& expected, const T& actual) {
    if (expected == actual) {
        std::cout << "[PASS] " << testName << '\n';
    } else {
        std::cout << "[FAIL] " << testName
                  << " | Expected: " << expected
                  << ", Actual: " << actual << '\n';
    }
}

int main() {
    Solution solution;

    {
        auto input = ;
        auto expected = ;
        expectEqual("Sample1", expected, solution.method(input));
    }

    return 0;
}
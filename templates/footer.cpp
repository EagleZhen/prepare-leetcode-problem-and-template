/*

*/

int main() {
    Solution solution;

    vector<int> input, output;
    int i1, i2;

    input = {};
    i1 = 0;
    i2 = 0;
    output = solution.f(input);
    assert(output == vector<int>({1, 2, 3}));

    return 0;
}
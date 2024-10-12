/*

*/

int main(){
    Solution solution;

    vector<int> v1, output;
    int i1, i2;

    v1 = {};
    i1 = 0;
    i2 = 0;
    output = solution.f(v1);
    assert(output == vector<int>({1,2,3}));

    return 0;
}
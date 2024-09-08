int main(){
    Solution solution;

    vector<int> v1, v2;
    int i1, i2;

    v1 = {};
    i1 = 0;
    i2 = 0;
    v2 = solution.f(v1, v2);
    assert(v2 == vector<int>({1,2,3}));

    return 0;
}
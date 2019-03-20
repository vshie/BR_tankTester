/******************************************************************************
 * Simple Low Pass
 *
 * A bare-bones first-order low-pass filter.
 ******************************************************************************/

class LPFilter
{
  public:
    LPFilter();
    LPFilter(float dt, float tau);
    ~LPFilter();
    float step(float input);
    float getValue();
    void  setPeriod(float dt);
    void  setTimeConstant(float tau);

  private:
    void  _clearFilter();
    void  _generateTF(float dt, float tau);
    bool  _isInitialized();

    float _dt;                  // s
    float _tau;                 // s

    float _num[2];              // transfer function numerator
    float _den[2];              // transfer function denominator
    float _inputs[2];
    float _outputs[2];
};

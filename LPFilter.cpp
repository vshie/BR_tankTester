/******************************************************************************
 * Simple Low Pass
 *
 * A bare-bones first-order low-pass filter.
 ******************************************************************************/

#include "LPFilter.h"

//////////////////
// Constructors //
//////////////////

// Default Constructor
LPFilter::LPFilter()
{
  _dt   = -1;
  _tau  = -1;

  this->_clearFilter();
}

// Useful Constructor
LPFilter::LPFilter(float dt, float tau)
{
  _dt   = dt;
  _tau  = tau;

  this->_clearFilter();
  this->_generateTF(dt, tau);
}

// Destructor
LPFilter::~LPFilter() {} // Nothing to destruct


////////////////////
// Public Methods //
////////////////////

// Move filter along one timestep, return filtered output
float LPFilter::step(float input)
{
  float output = 0;

  if (this->_isInitialized()) {
    // Advance input array
    _inputs[1] = _inputs[0];
    _inputs[0] = input;

    // Run filter
    // Handle numerator
    for (int i = 0; i < 2; i++) {
      output += _num[i]*_inputs[i];
    }
    // Handle denominator
    for (int i = 1; i < 2; i++) {
      output -= _den[i]*_outputs[i-1];
    }
    // Divide out first denominator term
    output /= _den[0];

    // Advance output array
    _outputs[1] = _outputs[0];
    _outputs[0] = output;
  }

  return output;
}

// Return the most recent filtered value without stepping filter
float LPFilter::getValue()
{
  return _outputs[0];
}

// Set filter period, _dt (s)
void  LPFilter::setPeriod(float dt)
{
  _dt = dt;

  if (this->_isInitialized()) {
    this->_generateTF(_dt, _tau);
  }
}

// Set filter time constant, _tau (s)
void  LPFilter::setTimeConstant(float tau)
{
  _tau = tau;

  if (this->_isInitialized()) {
    this->_generateTF(_dt, _tau);
  }
}


/////////////////////
// Private Methods //
/////////////////////

// Reset input/output arrays to 0.
void  LPFilter::_clearFilter()
{
  _inputs[0]  = 0;
  _inputs[1]  = 0;
  _outputs[0] = 0;
  _outputs[1] = 0;
}

// Generate transfer function
void  LPFilter::_generateTF(float dt, float tau)
{
  _num[0] = dt/tau;
  _num[1] = 0;
  _den[0] = 1;
  _den[1] = dt/tau - 1;
}

// Check whether the filter has been initialized (i.e. _dt, _tau != -1)
bool LPFilter::_isInitialized()
{
  return (_dt > 0) && (_tau > 0);
}

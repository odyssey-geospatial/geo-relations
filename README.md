
# geo-relations

### Generate datasets to test geometric relationships
	
This package generates datasets that can be used to test code that 
describes spatial relationships between things. 
For example, if you have something that determines whether two lines intersect,
then you can crate a dataset of thousands of line pairs, soe of which intersect and
some of which don't. 

The intended use of this package is to test methods that estimate
geometric relationships based on approximate positional encodings. 
For example, "given approximate encodings for a pair of lines,
how well can I determine whether the lines intersect?"

In order to give the data some realism, this package pulls shapes of 
various entities from OpenStreetMap. It then moves and shifts them
around in order to assure that prescribed relationships either
do or  do not exist between them.


## Supporting packages

* `shapely`: Provides computations on geometric objects.
* `osmnx`: Used to pull shapes from OpenStreetMap. See: Boeing, G. (2024). Modeling and Analyzing Urban Networks and Amenities with OSMnx. Working paper. https://geoffboeing.com/publications/osmnx-paper/

## Installation

```python
pip install geo-relations
```

## Release History

* 1.0.0: Coming soon

## Author and maintainers

* John Collins -- `john@odyssey-geospatial.com`

## Contributing

1. Fork the repo (https://github.com/yourname/yourproject/fork)
2. Create your feature branch (git checkout -b feature/fooBar)
3. Commit your changes (git commit -am 'Add some fooBar')
4. Push to the branch (git push origin feature/fooBar)
5. Create a new Pull Request

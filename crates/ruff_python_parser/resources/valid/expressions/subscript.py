data[0][0]
data[0, 1]
data[0:,]
data[0:, 1]
data[0:1, 2]
data[0:1:2, 3, a:b + 1]
data[a := b]
data[:, :11]
data[1, 2, 3]
data[~flag]
data[(a := 0):]
data[(a := 0):y]

# This is a single element tuple with a starred expression
data[*x]
data[*x and y]
data[*(x := y)]
